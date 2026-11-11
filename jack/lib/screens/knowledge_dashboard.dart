/// Knowledge Core dashboard (M4.8).
library jack_knowledge_dashboard;

import 'package:flutter/material.dart';

import '../models/knowledge_models.dart';
import '../services/knowledge_api_service.dart';
import 'document_manager.dart';
import 'knowledge_explorer.dart';
import 'knowledge_graph.dart';
import 'knowledge_validation.dart';

class KnowledgeDashboardScreen extends StatefulWidget {
  const KnowledgeDashboardScreen({super.key});

  @override
  State<KnowledgeDashboardScreen> createState() =>
      _KnowledgeDashboardScreenState();
}

class _KnowledgeDashboardScreenState extends State<KnowledgeDashboardScreen> {
  final KnowledgeApiService _api = KnowledgeApiService();

  KnowledgeHealth? _health;
  List<KnowledgeDomain> _domains = [];
  List<KnowledgeItem> _items = [];
  List<KnowledgeSource> _sources = [];
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
      final health = await _api.getHealth();
      final domains = await _api.listDomains();
      final items = await _api.listItems(limit: 20);
      final sources = await _api.listDocuments();
      if (mounted) {
        setState(() {
          _health = health;
          _domains = domains;
          _items = items;
          _sources = sources;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _loading = false;
        });
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
        title: const Text('Knowledge Core'),
        backgroundColor: const Color(0xFF151719),
        foregroundColor: const Color(0xFFE5E2DE),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: <Widget>[
          const Text('M4.8 Knowledge Core',
              style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600,
                  letterSpacing: 1.2, color: Color(0xFFEA9229))),
          const SizedBox(height: 16),
          Container(
            margin: const EdgeInsets.only(bottom: 16),
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
                  const Text('STATO MOTORE',
                      style: TextStyle(fontSize: 10,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 1.2,
                          color: Color(0xFFEA9229))),
                  const SizedBox(height: 8),
                  Text('Schema: v${_health?.schemaVersion ?? 0}',
                      style: const TextStyle(fontSize: 14)),
                  const SizedBox(height: 8),
                  Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: _health?.status == 'ok'
                          ? const Color(0xFF7FC69D)
                          : const Color(0xFFE85D5D),
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(_health?.status ?? 'sconosciuto',
                      style: const TextStyle(fontSize: 12)),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Container(
            margin: const EdgeInsets.only(bottom: 16),
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
                  const Text('STATISTICHE',
                      style: TextStyle(fontSize: 10,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 1.2,
                          color: Color(0xFFEA9229))),
                  const SizedBox(height: 12),
                  Row(
                    children: <Widget>[
                      Expanded(child: _statCard('Elementi', _items.length.toString())),
                      Expanded(child: _statCard('Domini', _domains.length.toString())),
                      Expanded(child: _statCard('Documenti', _sources.length.toString())),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Container(
            margin: const EdgeInsets.only(bottom: 16),
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
                  const Text('ELEMENTI RECENTI',
                      style: TextStyle(fontSize: 10,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 1.2,
                          color: Color(0xFFEA9229))),
                  const SizedBox(height: 12),
                  if (_items.isEmpty)
                    const Text('Nessun elemento di conoscenza.',
                        style: TextStyle(fontSize: 11))
                  else
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: _items.take(5).map((item) {
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: Row(
                            children: <Widget>[
                              Expanded(
                                child: Text(item.title,
                                    style: const TextStyle(fontSize: 13),
                                    overflow: TextOverflow.ellipsis),
                              ),
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
                            ],
                          ),
                        );
                      }).toList(),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Container(
            margin: const EdgeInsets.only(bottom: 16),
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
                  const Text('DOCUMENTI IMPORTATI',
                      style: TextStyle(fontSize: 10,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 1.2,
                          color: Color(0xFFEA9229))),
                  const SizedBox(height: 12),
                  if (_sources.isEmpty)
                    const Text('Nessun documento importato.',
                        style: TextStyle(fontSize: 11))
                  else
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: _sources.take(5).map((source) {
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: Text(source.title,
                              style: const TextStyle(fontSize: 13),
                              overflow: TextOverflow.ellipsis),
                        );
                      }).toList(),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Container(
            margin: const EdgeInsets.only(bottom: 16),
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
                  const Text('NAVIGAZIONE',
                      style: TextStyle(fontSize: 10,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 1.2,
                          color: Color(0xFFEA9229))),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          onPressed: () => Navigator.push(context,
                              MaterialPageRoute(builder: (_) => const KnowledgeExplorerScreen())),
                          child: const Text('Esplora',
                              style: TextStyle(fontSize: 12,
                                  color: Color(0xFF67C8CD))),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: const Color(0xFF67C8CD),
                            side: const BorderSide(color: Color(0xFF67C8CD)),
                            fixedSize: const Size.fromHeight(36),
                          ),
                        ),
                      ),
                      Expanded(
                        child: OutlinedButton(
                          onPressed: () => Navigator.push(context,
                              MaterialPageRoute(builder: (_) => const KnowledgeGraphScreen())),
                          child: const Text('Grafo',
                              style: TextStyle(fontSize: 12,
                                  color: Color(0xFF67C8CD))),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: const Color(0xFF67C8CD),
                            side: const BorderSide(color: Color(0xFF67C8CD)),
                            fixedSize: const Size.fromHeight(36),
                          ),
                        ),
                      ),
                      Expanded(
                        child: OutlinedButton(
                          onPressed: () => Navigator.push(context,
                              MaterialPageRoute(builder: (_) => const DocumentManagerScreen())),
                          child: const Text('Documenti',
                              style: TextStyle(fontSize: 12,
                                  color: Color(0xFF67C8CD))),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: const Color(0xFF67C8CD),
                            side: const BorderSide(color: Color(0xFF67C8CD)),
                            fixedSize: const Size.fromHeight(36),
                          ),
                        ),
                      ),
                      Expanded(
                        child: OutlinedButton(
                          onPressed: () => Navigator.push(context,
                              MaterialPageRoute(builder: (_) => const KnowledgeValidationScreen())),
                          child: const Text('Approvazioni',
                              style: TextStyle(fontSize: 12,
                                  color: Color(0xFF67C8CD))),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: const Color(0xFF67C8CD),
                            side: const BorderSide(color: Color(0xFF67C8CD)),
                            fixedSize: const Size.fromHeight(36),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
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
              fontWeight: FontWeight.w700, color: Color(0xFFEA9229))),
        ],
      ),
    );
  }
}
