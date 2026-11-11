/// Knowledge Validation (M4.7).
/// Gestisce approvazione/rifiuto proposte usando solo API reali.
library jack_knowledge_validation;

import 'package:flutter/material.dart';

import '../models/knowledge_models.dart';
import '../services/knowledge_api_service.dart';

class KnowledgeValidationScreen extends StatefulWidget {
  const KnowledgeValidationScreen({super.key});

  @override
  State<KnowledgeValidationScreen> createState() =>
      _KnowledgeValidationScreenState();
}

class _KnowledgeValidationScreenState extends State<KnowledgeValidationScreen> {
  final KnowledgeApiService _api = KnowledgeApiService();
  List<KnowledgeProposal> _proposals = [];
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
      final proposals = await _api.listProposals(processState: 'pending');
      if (mounted) setState(() {
        _proposals = proposals;
        _loading = false;
      });
    } catch (e) {
      if (mounted) setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _approve(String proposalId) async {
    setState(() => _loading = true);
    try {
      await _api.approveProposal(proposalId);
      await _load();
    } catch (e) {
      if (mounted) {
        setState(() => _loading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Errore approvazione: $e',
                style: const TextStyle(color: Color(0xFFE5E2DE))),
            backgroundColor: const Color(0xFFE85D5D),
          ),
        );
      }
    }
  }

  Future<void> _reject(String proposalId) async {
    setState(() => _loading = true);
    try {
      await _api.rejectProposal(proposalId);
      await _load();
    } catch (e) {
      if (mounted) {
        setState(() => _loading = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Errore rifiuto: $e',
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
        title: const Text('Knowledge Validation'),
        backgroundColor: const Color(0xFF151719),
        foregroundColor: const Color(0xFFE5E2DE),
      ),
      body: Column(
        children: <Widget>[
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16),
            child: Text('M4.7 Validazione proposte',
                style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600,
                    letterSpacing: 1.2, color: Color(0xFFEA9229))),
          ),
          const SizedBox(height: 16),
          Expanded(
            child: _proposals.isEmpty
                ? const Center(
                    child: Text('Nessuna proposta in attesa.',
                        style: TextStyle(fontSize: 11,
                            color: Color(0xFF88898B))))
                : ListView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: _proposals.length,
                    itemBuilder: (ctx, i) {
                      final p = _proposals[i];
                      return _proposalCard(p);
                    },
                  ),
          ),
        ],
      ),
    );
  }

  Widget _proposalCard(KnowledgeProposal p) {
    return Card(
      color: const Color(0xFF1D2023),
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(p.title,
                          style: const TextStyle(fontSize: 15,
                              color: Color(0xFFE5E2DE))),
                      const SizedBox(height: 8),
                      Text(p.content,
                          style: const TextStyle(fontSize: 13,
                              color: Color(0xFF88898B)),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis),
                    ],
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: <Widget>[
                    Text(p.processState.toUpperCase(),
                        style: const TextStyle(fontSize: 11,
                            color: Color(0xFFEA9229),
                            fontWeight: FontWeight.w600)),
                    const SizedBox(height: 8),
                    Row(
                      children: <Widget>[
                        ElevatedButton(
                          onPressed: () => _approve(p.id),
                          child: const Text('Approva'),
                        ),
                        const SizedBox(width: 8),
                        ElevatedButton(
                          onPressed: () => _reject(p.id),
                          style: ElevatedButton.styleFrom(
                              backgroundColor: Color(0xFFE85D5D)),
                          child: const Text('Rifiuta'),
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: <Widget>[
                _chip(p.knowledgeType),
                const SizedBox(width: 8),
                _chip(p.verificationStatus),
                const SizedBox(width: 8),
                _chip('Conf: ${(p.confidenceScore * 100).toInt()}%'),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _chip(String label) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: const Color(0xFF1D2023),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: const Color(0xFF24272A)),
      ),
      child: Text(label, style: const TextStyle(fontSize: 11)),
    );
  }
}
