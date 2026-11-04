import 'dart:async';
import 'dart:convert';
import 'dart:io';

class LocalApiException implements Exception {
  const LocalApiException({required this.message, this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

class LocalApiClient {
  LocalApiClient({
    Uri? baseUri,
    this.timeout = const Duration(milliseconds: 1800),
  }) : _baseUri =
           baseUri ??
           Uri.parse(
             const String.fromEnvironment(
               'JACK_BACKEND_URL',
               defaultValue: 'http://127.0.0.1:8000',
             ),
           );

  final Uri _baseUri;
  final Duration timeout;

  Future<Object?> getJson(
    String path, {
    Map<String, String>? queryParameters,
  }) => _request(
    'GET',
    path,
    queryParameters: queryParameters,
    acceptedStatuses: const {HttpStatus.ok},
  );

  Future<Object?> postJson(String path, Object body) => _request(
    'POST',
    path,
    body: body,
    acceptedStatuses: const {HttpStatus.created},
  );

  Future<Object?> putJson(String path, Object body) => _request(
    'PUT',
    path,
    body: body,
    acceptedStatuses: const {HttpStatus.ok},
  );

  Future<void> delete(String path) async {
    await _request(
      'DELETE',
      path,
      acceptedStatuses: const {HttpStatus.noContent},
    );
  }

  Future<Object?> _request(
    String method,
    String path, {
    Object? body,
    Map<String, String>? queryParameters,
    required Set<int> acceptedStatuses,
  }) async {
    final client = HttpClient()..connectionTimeout = timeout;
    try {
      var uri = _baseUri.resolve(path);
      if (queryParameters != null && queryParameters.isNotEmpty) {
        uri = uri.replace(queryParameters: queryParameters);
      }

      final request = await client.openUrl(method, uri).timeout(timeout);
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      if (body != null) {
        request.headers.contentType = ContentType.json;
        request.write(jsonEncode(body));
      }

      final response = await request.close().timeout(timeout);
      final responseText = await utf8.decoder
          .bind(response)
          .join()
          .timeout(timeout);
      if (!acceptedStatuses.contains(response.statusCode)) {
        throw LocalApiException(
          statusCode: response.statusCode,
          message: _messageForStatus(response.statusCode),
        );
      }
      if (responseText.isEmpty) return null;
      try {
        return jsonDecode(responseText);
      } on FormatException {
        throw LocalApiException(
          statusCode: response.statusCode,
          message: 'Il backend locale ha restituito una risposta non valida.',
        );
      }
    } on LocalApiException {
      rethrow;
    } on SocketException {
      throw const LocalApiException(
        message: 'Backend locale offline. Avvia J.A.C.K. Backend e riprova.',
      );
    } on TimeoutException {
      throw const LocalApiException(
        message:
            'Il backend locale non risponde. Verifica che sia in esecuzione.',
      );
    } on IOException {
      throw const LocalApiException(
        message: 'Impossibile comunicare con il backend locale.',
      );
    } finally {
      client.close(force: true);
    }
  }

  String _messageForStatus(int statusCode) => switch (statusCode) {
    HttpStatus.notFound => 'Il ricordo richiesto non è stato trovato.',
    HttpStatus.unprocessableEntity =>
      'Dati non validi. Controlla i campi inseriti.',
    HttpStatus.conflict =>
      'Esiste già un collegamento equivalente tra queste memorie.',
    >= HttpStatus.internalServerError =>
      'Errore del backend locale. I dati mostrati non sono stati modificati.',
    _ => 'Richiesta non completata (HTTP $statusCode).',
  };
}
