library jack_document_manager;

import 'package:flutter/material.dart';

import '../models/knowledge_models.dart';
import '../services/knowledge_api_service.dart';

class DocumentManagerScreen extends StatefulWidget {
  const DocumentManagerScreen({super.key});

  @override
  State<DocumentManagerScreen> createState() => _DocumentManagerScreenState();
}

class _DocumentManagerScreenState extends State<DocumentManagerScreen> {
  final KnowledgeApiService _api = KnowledgeApiService();
  List<KnowledgeSource> _sources = [];
  bool _loading = true;
  String? _error;
  String? _newFilePath;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final sources = await _api.listDocuments();
      if (mounted) setState(() {
        _sources = sources;
        _loading = false;
      });
    } catch (e) {
      if (mounted) setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _importFile() async {
    final controller = TextEditingController(text: _newFilePath ?? '');
    final result = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Importa documento'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(
            hintText: 'Percorso file locale (es. /percorso/documento.pdf)',
          ),
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Annulla'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, controller.text.trim()),
            child: const Text('Importa'),
          ),
        ],
      ),
    );
    if (result == null || result.isEmpty) return;
    setState(() => _loading = true);
    try {
      await _api.importDocumentFile(filePath: result);
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('Documento importato',
                style: TextStyle(color: Color(0xFFE5E2DE))),
            backgroundColor: const Color(0xFF67C8CD),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() => _loading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Errore import: $e',
                style: const TextStyle(color: Color(0xFFE5E2DE))),
            backgroundColor: const Color(0xFFE85D5D),
          ),
        );
      }
    }
  }

  Future<void> _reprocess(String sourceId) async {
    setState(() => _loading = true);
    try {
      await _api.reprocessDocument(sourceId: sourceId);
      await _load();
    } catch (e) {
      if (mounted) {
        setState(() => _loading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Errore riprocesso: $e',
                style: const TextStyle(color: Color(0xFFE5E2DE))),
            backgroundColor: const Color(0xFFE85D5D),
          ),
        );
      }
    }
  }

  Future<void> _delete(String sourceId) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Elimina documento'),
        content: const Text('Eliminare definitivamente questo documento?'),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Annulla'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Elimina'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _loading = true);
    try {
      await _api.deleteDocument(sourceId);
      await _load();
    } catch (e) {
      if (mounted) {
        setState(() => _loading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Errore eliminazione: $e',
                style: const TextStyle(color: Color(0xFFE5E2DE))),
            backgroundColor: const Color(0xFFE85D5D),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(
        child: CircularProgressIndicator(color: Color(0xFFEA9229)),
      );
    }
    if (_error != null) {
      return Center(
        child: Text('Errore: $_error',
            style: const TextStyle(color: Color(0xFFE85D5D))),
      );
    }

    return Scaffold(
      backgroundColor: const Color(0xFF0D0F11),
      appBar: AppBar(
        title: const Text('Document Manager'),
        backgroundColor: const Color(0xFF151719),
        foregroundColor: const Color(0xFFE5E2DE),
        actions: <Widget>[
          IconButton(
            icon: const Icon(Icons.import_export, color: Color(0xFF67C8CD)),
            onPressed: _importFile,
            tooltip: 'Importa documento',
          ),
        ],
      ),
      body: Column(
        children: <Widget>[
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16),
            child: Text('M4.3 Document Intelligence',
                style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600,
                    letterSpacing: 1.2, color: Color(0xFFEA9229))),
          ),
          const SizedBox(height: 16),
          Container(
            margin: const EdgeInsets.symmetric(horizontal: 16),
            decoration: BoxDecoration(
              color: const Color(0xFF1D2023),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFF24272A)),
            ),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  const Text('Importa documento',
                      style: TextStyle(fontSize: 16,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFFE5E2DE))),
                  const SizedBox(height: 12),
                  Row(
                    children: <Widget>[
                      Expanded(
                        child: TextField(
                          decoration: const InputDecoration(
                            hintText: 'Percorso file locale',
                            hintStyle: TextStyle(color: Color(0xFF88898B)),
                          ),
                          style: const TextStyle(color: Color(0xFFE5E2DE)),
                          onChanged: (v) => _newFilePath = v,
                        ),
                      ),
                      const SizedBox(width: JackSpacing.s),
                      ElevatedButton(
                        onPressed: _newFilePath != null ? _importFile : null,
                        child: const Text('Importa'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Expanded(
            child: _sources.isEmpty
                ? const Center(
                    child: Text('Nessun documento importato.',
                        style: TextStyle(fontSize: 11,
                            color: Color(0xFF88898B))))
                : ListView.builder(
                    itemCount: _sources.length,
                    itemBuilder: (ctx, i) {
                      final s = _sources[i];
                      return ListTile(
                        title: Text(s.title,
                            style: const TextStyle(fontSize: 13,
                                color: Color(0xFFE5E2DE))),
                        subtitle: Text(
                            '${s.documentType} • ${s.pageCount ?? 0} pagine',
                            style: const TextStyle(fontSize: 11,
                                color: Color(0xFF88898B))),
                        trailing: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: <Widget>[
                            IconButton(
                              icon: const Icon(Icons.refresh,
                                  color: Color(0xFF67C8CD)),
                              onPressed: () => _reprocess(s.id),
                              tooltip: 'Riprocessa',
                            ),
                            IconButton(
                              icon: const Icon(Icons.delete,
                                  color: Color(0xFFE85D5D)),
                              onPressed: () => _delete(s.id),
                              tooltip: 'Elimina',
                            ),
                          ],
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}

class JackSpacing {
  static const double s = 8;
  static const double m = 16;
}
