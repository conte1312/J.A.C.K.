import 'dart:convert';
import 'dart:io';

import '../models/ai_hub_configuration.dart';

class AiHubStorageException implements Exception {
  const AiHubStorageException(this.message, {this.cause});

  final String message;
  final Object? cause;

  @override
  String toString() => message;
}

class AiHubDemoRepository {
  AiHubDemoRepository({File? file}) : _file = file ?? _defaultConfigFile();

  final File _file;

  Future<AiHubConfiguration> load() async {
    try {
      if (!await _file.exists()) return AiHubConfiguration.demoDefaults();
      final decoded = jsonDecode(await _file.readAsString());
      return AiHubConfiguration.fromJson(decoded);
    } on FileSystemException catch (error) {
      throw AiHubStorageException(
        'Non riesco a leggere la configurazione demo locale.',
        cause: error,
      );
    } on FormatException catch (error) {
      throw AiHubStorageException(
        'La configurazione AI Hub non è valida. Puoi riprovare o ripristinare i dati demo.',
        cause: error,
      );
    }
  }

  Future<void> save(AiHubConfiguration configuration) async {
    configuration.validate();
    final temporaryFile = File('${_file.path}.tmp');
    try {
      await _file.parent.create(recursive: true);
      await temporaryFile.writeAsString(
        const JsonEncoder.withIndent('  ').convert(configuration.toJson()),
        flush: true,
      );
      await temporaryFile.rename(_file.path);
    } on FileSystemException catch (error) {
      if (await temporaryFile.exists()) {
        await temporaryFile.delete();
      }
      throw AiHubStorageException(
        'Non riesco a salvare la configurazione demo locale.',
        cause: error,
      );
    }
  }

  static File _defaultConfigFile() {
    final home = Platform.environment['HOME'];
    if (home == null || home.isEmpty) {
      throw const AiHubStorageException(
        'La cartella utente macOS non è disponibile per la configurazione locale.',
      );
    }
    final separator = Platform.pathSeparator;
    return File(
      '$home${separator}Library${separator}Application Support${separator}J.A.C.K.${separator}ai_hub_demo.json',
    );
  }
}
