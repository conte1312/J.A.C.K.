/// Knowledge Explorer (M4.2+).
library jack_knowledge_explorer;

import 'package:flutter/material.dart';

import '../models/knowledge_models.dart';
import '../services/knowledge_api_service.dart';

class KnowledgeExplorerScreen extends StatefulWidget {
  const KnowledgeExplorerScreen({super.key});

  @override
  State<KnowledgeExplorerScreen> createState() =>
      _KnowledgeExplorerScreenState();
}

class _KnowledgeExplorerScreenState extends State<KnowledgeExplorerScreen> {
  final KnowledgeApiService _api = KnowledgeApiService();
  final TextEditingController _queryCtrl = TextEditingController();
  List<KnowledgeItem> _items = [];
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _search();
  }

  Future<void> _search() async {
    setState(() => _loading = true);
    try {
      final items = await _api.listItems(
        query: _queryCtrl.text.isEmpty ? null : _queryCtrl.text,
        limit: 50,
      );
      if (mounted) setState(() {
        _items = items;
        _loading = false;
      });
    } catch (e) {
      if (mounted) setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D0F11),
      appBar: AppBar(
        title: const Text('Knowledge Explorer'),
        backgroundColor: const Color(0xFF151719),
        foregroundColor: const Color(0xFFE5E2DE),
      ),
      body: Column(
        children: <Widget>[
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16),
            child: Text('M4.2 Knowledge API',
                style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600,
                    letterSpacing: 1.2, color: Color(0xFFEA9229))),
          ),
          const SizedBox(height: 16),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: TextField(
              controller: _queryCtrl,
              decoration: const InputDecoration(
                hintText: 'Cerca conoscenza...',
                prefixIcon: Icon(Icons.search, size: 16,
                    color: Color(0xFF88898B)),
              ),
              style: const TextStyle(color: Color(0xFFE5E2DE)),
              onSubmitted: (_) => _search(),
            ),
          ),
          const SizedBox(height: 16),
          Expanded(
            child: _loading
                ? const Center(
                    child: CircularProgressIndicator(color: Color(0xFFEA9229)))
                : _error != null
                    ? Center(
                        child: Text('Errore: $_error',
                            style: const TextStyle(color: Color(0xFFE85D5D))))
                    : _items.isEmpty
                        ? const Center(
                            child: Text('Nessun elemento trovato.',
                                style: TextStyle(fontSize: 11,
                                    color: Color(0xFF88898B))))
                        : ListView.builder(
                            itemCount: _items.length,
                            itemBuilder: (ctx, i) {
                              final it = _items[i];
                              return ListTile(
                                title: Text(it.title,
                                    style: const TextStyle(fontSize: 13)),
                                subtitle: Text(
                                    '${it.knowledgeType} • ${it.verificationStatus}',
                                    style: const TextStyle(fontSize: 11,
                                        color: Color(0xFF88898B))),
                                trailing: Container(
                                  width: 6,
                                  height: 6,
                                  decoration: BoxDecoration(
                                    color: it.verificationStatus == 'verified'
                                        ? const Color(0xFF7FC69D)
                                        : const Color(0xFFEA9229),
                                    shape: BoxShape.circle,
                                  ),
                                ),
                                onTap: () => _showItemDetail(it),
                              );
                            },
                          ),
          ),
        ],
      ),
    );
  }

  void _showItemDetail(KnowledgeItem item) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1D2023),
        title: Text(item.title,
            style: const TextStyle(color: Color(0xFFE5E2DE))),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Text('Tipo: ${item.knowledgeType}',
                  style: const TextStyle(fontSize: 11,
                      color: Color(0xFF88898B))),
              Text('Verifica: ${item.verificationStatus}',
                  style: const TextStyle(fontSize: 11,
                      color: Color(0xFF88898B))),
              Text('Stato: ${item.itemState}',
                  style: const TextStyle(fontSize: 11,
                      color: Color(0xFF88898B))),
              const SizedBox(height: 8),
              Text(item.content,
                  style: const TextStyle(fontSize: 13,
                      color: Color(0xFFE5E2DE))),
            ],
          ),
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Chiudi'),
          ),
        ],
      ),
    );
  }
}
