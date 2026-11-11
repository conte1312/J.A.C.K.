/// Knowledge Graph (M4.5+).
/// Visualizzazione semplificata del grafo della conoscenza usando solo API reali.
library jack_knowledge_graph;

import 'package:flutter/material.dart';

import '../models/knowledge_models.dart';
import '../services/knowledge_api_service.dart';

class KnowledgeGraphScreen extends StatefulWidget {
  const KnowledgeGraphScreen({super.key});

  @override
  State<KnowledgeGraphScreen> createState() => _KnowledgeGraphScreenState();
}

class _KnowledgeGraphScreenState extends State<KnowledgeGraphScreen> {
  final KnowledgeApiService _api = KnowledgeApiService();
  List<KnowledgeItem> _items = [];
  List<KnowledgeLink> _links = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final items = await _api.listItems(limit: 50);
      final links = await _api.listLinks(limit: 100);
      if (mounted) setState(() {
        _items = items;
        _links = links;
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
        title: const Text('Knowledge Graph'),
        backgroundColor: const Color(0xFF151719),
        foregroundColor: const Color(0xFFE5E2DE),
      ),
      body: Column(
        children: <Widget>[
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16),
            child: Text('M4.5 Knowledge Graph',
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
                  const Text('Statistiche grafo',
                      style: TextStyle(fontSize: 16,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFFE5E2DE))),
                  const SizedBox(height: 12),
                  Row(
                    children: <Widget>[
                      Expanded(child: _statCard('Nodi', _items.length.toString())),
                      Expanded(child: _statCard('Archi', _links.length.toString())),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Expanded(
            child: _items.isEmpty
                ? const Center(
                    child: Text('Nessun elemento nel grafo.',
                        style: TextStyle(fontSize: 11,
                            color: Color(0xFF88898B))))
                : _graphView(),
          ),
        ],
      ),
    );
  }

  Widget _statCard(String label, String value) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF1D2023),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF24272A)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(label, style: const TextStyle(fontSize: 11,
              color: Color(0xFF88898B))),
          const SizedBox(height: 4),
          Text(value, style: const TextStyle(fontSize: 20,
              fontWeight: FontWeight.w700, color: Color(0xFF67C8CD))),
        ],
      ),
    );
  }

  Widget _graphView() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const Padding(
          padding: EdgeInsets.all(16),
          child: Text('Relazioni tra elementi',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500,
                  color: Color(0xFFE5E2DE))),
        ),
        Expanded(
          child: ListView.builder(
            itemCount: _links.length,
            itemBuilder: (ctx, i) {
              final link = _links[i];
              final from = _items.firstWhere(
                  (it) => it.id == link.fromId,
                  orElse: () => KnowledgeItem(
                    id: link.fromId, domainId: '', title: link.fromId,
                    content: '', knowledgeType: '', sourceType: '',
                    confidenceScore: 0, verificationStatus: '',
                    itemState: '', version: 1, isCurrent: true,
                    acquiredAt: DateTime.now(), createdAt: DateTime.now(),
                    updatedAt: DateTime.now(), tags: [], importance: 3,
                    excluded: false,
                  ),
                  );
              final to = _items.firstWhere(
                  (it) => it.id == link.toId,
                  orElse: () => KnowledgeItem(
                    id: link.toId, domainId: '', title: link.toId,
                    content: '', knowledgeType: '', sourceType: '',
                    confidenceScore: 0, verificationStatus: '',
                    itemState: '', version: 1, isCurrent: true,
                    acquiredAt: DateTime.now(), createdAt: DateTime.now(),
                    updatedAt: DateTime.now(), tags: [], importance: 3,
                    excluded: false,
                  ),
                  );
              return ListTile(
                title: Text('${from.title} → ${to.title}',
                    style: const TextStyle(fontSize: 13)),
                subtitle: Text('${link.relationType} (forza ${link.strength})',
                    style: const TextStyle(fontSize: 11,
                        color: Color(0xFF88898B))),
                trailing: Container(
                  width: 6,
                  height: 6,
                  decoration: BoxDecoration(
                    color: link.strength >= 3
                        ? const Color(0xFF7FC69D)
                        : const Color(0xFFEA9229),
                    shape: BoxShape.circle,
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}
