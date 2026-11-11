/// Shared API client for J.A.C.K. 2.0.
///
/// Talks to the local FastAPI backend on loopback 127.0.0.1:8000.
/// No credentials are stored here; they are handled by the backend/Keychain.
/// Errors are surfaced as typed exceptions, never swallowed silently.
library jack_api_client;

import 'dart:convert';

import 'package:http/http.dart' as http;

/// Base URL for the local backend (loopback only).
const String kBackendBaseUrl = 'http://127.0.0.1:8000';

/// Thrown when the backend is unreachable.
class BackendUnavailableException implements Exception {
  final String message;
  BackendUnavailableException([this.message = 'Backend non raggiungibile.']);
  @override
  String toString() => 'BackendUnavailableException: $message';
}

/// Thrown when the backend returns an error status.
class ApiErrorException implements Exception {
  final int statusCode;
  final String message;
  ApiErrorException(this.statusCode, this.message);
  @override
  String toString() => 'ApiErrorException: $statusCode $message';
}

/// Thrown when the response cannot be decoded.
class ApiDecodeException implements Exception {
  final String message;
  ApiDecodeException(this.message);
  @override
  String toString() => 'ApiDecodeException: $message';
}

/// Minimal JSON API client with structured error handling.
class JackApiClient {
  JackApiClient({this.baseUrl = kBackendBaseUrl, this.client});

  final String baseUrl;
  final http.Client? client;

  http.Client get _effectiveClient => client ?? http.Client();

  Future<Map<String, dynamic>> get(
    String path, {
    Map<String, String>? headers,
  }) async {
    final uri = Uri.parse('$baseUrl$path');
    try {
      final response = await _effectiveClient.get(uri, headers: headers);
      return _handle(response);
    } on ApiErrorException {
      rethrow;
    } on BackendUnavailableException {
      rethrow;
    } catch (e) {
      throw BackendUnavailableException('Errore contattando il backend: $e');
    }
  }

  Future<Map<String, dynamic>> post(
    String path, {
    Map<String, dynamic>? body,
    Map<String, String>? headers,
  }) async {
    final uri = Uri.parse('$baseUrl$path');
    try {
      final response = await _effectiveClient.post(
        uri,
        headers: {...?headers, 'Content-Type': 'application/json'},
        body: body == null ? null : jsonEncode(body),
      );
      return _handle(response);
    } on ApiErrorException {
      rethrow;
    } on BackendUnavailableException {
      rethrow;
    } catch (e) {
      throw BackendUnavailableException('Errore contattando il backend: $e');
    }
  }

  Map<String, dynamic> _handle(http.Response response) {
    if (response.statusCode >= 500) {
      throw BackendUnavailableException(
        'Backend errore: ${response.statusCode}',
      );
    }
    if (response.statusCode >= 400) {
      String detail = 'Richiesta non valida';
      try {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>?;
        detail = decoded?['detail']?.toString() ?? detail;
      } catch (_) {}
      throw ApiErrorException(response.statusCode, detail);
    }
    try {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } catch (e) {
      throw ApiDecodeException('Impossibile decodificare la risposta: $e');
    }
  }
}
