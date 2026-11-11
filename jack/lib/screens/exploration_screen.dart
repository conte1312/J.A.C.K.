/// Esplorazione — mappa visiva di memorie e collegamenti (Knowledge Graph).
/// Usa API reali del backend per caricare nodi e relazioni.
library jack_exploration;

import 'package:flutter/material.dart';

import '../models/knowledge_models.dart';
import '../services/knowledge_api_service.dart';

class ExplorationScreen extends StatefulWidget {
  const ExplorationScreen({super.key});

  @override
  State<ExplorationScreen> createState() => _ExplorationScreenState();
}

class _ExplorationScreenState extends State<ExplorationScreen> {
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
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final results = await Future.wait<Object?>([
        _api.listItems(limit: 50),
        _api.listLinks(limit: 100),
      ]);
      if (!mounted) return;
      setState(() {
        _items = results[0] as List<KnowledgeItem>;
        _links = results[1] as List<KnowledgeLink>;
        _loading = false;
      });
    } on Exception catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString();
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(
        backgroundColor: Color(0xFF0D0F11),
        body: Center(
          child: CircularProgressIndicator(color: Color(0xFFEA9229)),
        ),
      );
    }

    if (_error != null) {
      return Scaffold(
        backgroundColor: Color(0xFF0D0F11),
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline,
                  color: Color(0xFFE85D5D), size: 48),
              const SizedBox(height: 12),
              Text('Errore: $_error',
                  style: const TextStyle(color: Color(0xFFE5E2DE))),
              const SizedBox(height: 16),
              OutlinedButton.icon(
                onPressed: _load,
                icon: const Icon(Icons.refresh, size: 16),
                label: const Text('Riprova',
                    style: TextStyle(color: Color(0xFF67C8CD))),
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFF67C8CD),
                  side: const BorderSide(color: Color(0xFF67C8CD)),
                ),
              ),
            ],
          ),
        ),
      );
    }

    if (_items.isEmpty) {
      return Scaffold(
        backgroundColor: const Color(0xFF0D0F11),
        body: const Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.explore_outlined,
                  color: Color(0xFF67C8CD), size: 48),
              SizedBox(height: 16),
              Text('Nessuna conoscenza da esplorare.',
                  style: TextStyle(color: Color(0xFFE5E2DE))),
              SizedBox(height: 8),
              Text('Importa documenti o crea elementi nella Knowledge Dashboard.',
                  style: TextStyle(color: Color(0xFF88898B), fontSize: 12),
                  textAlign: TextAlign.center),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: const Color(0xFF0D0F11),
      appBar: AppBar(
        title: const Text('Esplorazione'),
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
          Expanded(
            child: _GraphView(items: _items, links: _links),
          ),
        ],
      ),
    );
  }
}

class _GraphView extends StatelessWidget {
  final List<KnowledgeItem> items;
  final List<KnowledgeLink> links;

  const _GraphView({required this.items, required this.links});

  @override
  Widget build(BuildContext context) {
    return Container(
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
          children: [
            Text(
              'Nodi: ${items.length} · Relazioni: ${links.length}',
              style: const TextStyle(
                color: Color(0xFF88898B),
                fontSize: 12,
              ),
            ),
            const SizedBox(height: 12),
            Expanded(
              child: ListView.builder(
                itemCount: items.length,
                itemBuilder: (context, index) {
                  final item = items[index];
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Row(
                      children: [
                        Container(
                          width: 6,
                          height: 6,
                          decoration: BoxDecoration(
                            color: item.verificationStatus == 'verified'
                                ? const Color(0xFF7FC69D)
                                : const Color(0xFFEA9229),
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            item.title,
                            style: const TextStyle(
                              color: Color(0xFFE5E2DE),
                              fontSize: 13,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 2),
                          decoration: BoxDecoration(
                            color: const Color(0xFF24272A),
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(
                                color: const Color(0xFF67C8CD)),
                          ),
                          child: Text(
                            item.knowledgeType,
                            style: const TextStyle(
                              color: Color(0xFF67C8CD),
                              fontSize: 10,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}
