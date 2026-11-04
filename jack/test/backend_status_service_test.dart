import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:jack/services/backend_status_service.dart';

void main() {
  test('reads health and info from a local HTTP service', () async {
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    final paths = <String>[];
    final subscription = server.listen((request) async {
      paths.add(request.uri.path);
      request.response.headers.contentType = ContentType.json;

      final body = switch (request.uri.path) {
        '/health' => {
          'status': 'ok',
          'app': 'J.A.C.K.',
          'service': 'J.A.C.K. Local Backend',
          'version': '0.1.0',
        },
        '/api/v1/info' => {
          'name': 'J.A.C.K. Local Backend',
          'version': '0.1.0',
          'modules': ['health', 'info', 'memories'],
        },
        _ => null,
      };

      if (body == null) {
        request.response.statusCode = HttpStatus.notFound;
      } else {
        request.response.write(jsonEncode(body));
      }
      await request.response.close();
    });

    addTearDown(() async {
      await subscription.cancel();
      await server.close(force: true);
    });

    final snapshot = await BackendStatusService(
      baseUri: Uri(
        scheme: 'http',
        host: InternetAddress.loopbackIPv4.address,
        port: server.port,
      ),
    ).check();

    expect(snapshot, isNotNull);
    expect(snapshot!.name, 'J.A.C.K. Local Backend');
    expect(snapshot.version, '0.1.0');
    expect(snapshot.modules, ['health', 'info', 'memories']);
    expect(paths, ['/health', '/api/v1/info']);
  });
}
