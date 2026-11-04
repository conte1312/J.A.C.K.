import 'package:flutter/material.dart';

import '../jack_primitives.dart';
import 'jack_core_graph.dart';

class JackCorePreviewPanel extends StatelessWidget {
  const JackCorePreviewPanel({
    required this.graph,
    required this.node,
    required this.onOpenInGraph,
    this.onClearSelection,
    super.key,
  });

  final JackCoreGraph graph;
  final JackCoreNode? node;
  final VoidCallback onOpenInGraph;
  final VoidCallback? onClearSelection;

  @override
  Widget build(BuildContext context) {
    final selectedNode = node;
    final relatedEdges = selectedNode == null
        ? const <JackCoreEdge>[]
        : graph.edges
              .where(
                (edge) =>
                    edge.fromId == selectedNode.id ||
                    edge.toId == selectedNode.id,
              )
              .toList(growable: false);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF17191C),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFF38352F)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              const Expanded(child: SectionEyebrow('Anteprima nodo')),
              if (graph.origin == JackCoreGraphOrigin.demo)
                const DemoBadge(label: 'GRAFO DEMO'),
              if (selectedNode != null && onClearSelection != null) ...[
                const SizedBox(width: 4),
                IconButton(
                  key: const ValueKey('clear-node-selection'),
                  tooltip: 'Rimuovi selezione',
                  onPressed: onClearSelection,
                  icon: const Icon(Icons.close_rounded, size: 16),
                  color: const Color(0xFF9B9B9C),
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints.tightFor(
                    width: 28,
                    height: 28,
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: 14),
          if (selectedNode == null)
            const _EmptyNodePreview()
          else ...[
            Text(
              selectedNode.title,
              key: const ValueKey('selected-node-title'),
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: Color(0xFFE8E5E0),
                fontSize: 16,
                height: 1.35,
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(height: 12),
            _MetadataRow(
              label: 'Categoria',
              value: _categoryLabel(selectedNode.category),
            ),
            _MetadataRow(
              label: 'Tipo',
              value: _sourceTypeLabel(selectedNode.sourceType),
            ),
            _MetadataRow(
              label: 'Provenienza',
              value: _available(selectedNode.source),
            ),
            _MetadataRow(
              label: 'Verifica',
              value: _verificationLabel(selectedNode.verification),
            ),
            _MetadataRow(
              label: 'Importanza',
              value: '${selectedNode.importance} / 5',
            ),
            _MetadataRow(
              label: 'Esclusione',
              value: selectedNode.excluded
                  ? 'Escluso dal recupero'
                  : 'Incluso nel recupero',
              valueColor: selectedNode.excluded
                  ? const Color(0xFFB8A88F)
                  : const Color(0xFF86C5A0),
            ),
            _MetadataRow(
              label: 'Ultimo uso',
              value: _lastUsedLabel(context, selectedNode.lastUsed),
            ),
            const SizedBox(height: 10),
            const Divider(height: 1, color: Color(0xFF303236)),
            const SizedBox(height: 10),
            const _SectionHeading('Tag'),
            const SizedBox(height: 6),
            if (selectedNode.tags.isEmpty)
              const Text(
                'Nessun tag',
                style: TextStyle(color: Color(0xFF9A9A9B), fontSize: 11),
              )
            else
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  for (final tag in selectedNode.tags) _TagPill(label: tag),
                ],
              ),
            if (selectedNode.content.isNotEmpty) ...[
              const SizedBox(height: 12),
              const _SectionHeading('Contenuto'),
              const SizedBox(height: 5),
              Text(
                selectedNode.content,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: Color(0xFFB8B7B5),
                  fontSize: 11,
                  height: 1.45,
                ),
              ),
            ],
            const SizedBox(height: 12),
            const Divider(height: 1, color: Color(0xFF303236)),
            const SizedBox(height: 10),
            Row(
              children: [
                const Expanded(child: _SectionHeading('Relazioni')),
                Text(
                  '${relatedEdges.length}',
                  style: const TextStyle(
                    color: Color(0xFF99999A),
                    fontSize: 11,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 7),
            if (relatedEdges.isEmpty)
              const Text(
                'Nessuna relazione disponibile',
                style: TextStyle(color: Color(0xFF9A9A9B), fontSize: 11),
              )
            else
              for (final edge in relatedEdges)
                _RelationRow(
                  edge: edge,
                  selectedNode: selectedNode,
                  graph: graph,
                ),
            if (graph.origin == JackCoreGraphOrigin.demo) ...[
              const SizedBox(height: 10),
              const Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    Icons.info_outline_rounded,
                    size: 13,
                    color: Color(0xFFC59A59),
                  ),
                  SizedBox(width: 7),
                  Expanded(
                    child: Text(
                      'Informazioni dimostrative, non provenienti da memorie personali.',
                      style: TextStyle(
                        color: Color(0xFFA9A39A),
                        fontSize: 10,
                        height: 1.4,
                      ),
                    ),
                  ),
                ],
              ),
            ],
            const SizedBox(height: 14),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                key: const ValueKey('open-selected-node-in-graph'),
                onPressed: onOpenInGraph,
                icon: const Icon(Icons.hub_outlined, size: 15),
                label: const Text('Apri in Esplorazione'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFFD2B375),
                  side: const BorderSide(color: Color(0xFF504333)),
                  minimumSize: const Size.fromHeight(38),
                  textStyle: const TextStyle(fontSize: 11),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(11),
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  String _categoryLabel(JackCoreCategory category) => switch (category) {
    JackCoreCategory.identity => 'Identità',
    JackCoreCategory.work => 'Lavoro',
    JackCoreCategory.projects => 'Progetti',
    JackCoreCategory.people => 'Persone',
    JackCoreCategory.technical => 'Tecnica',
    JackCoreCategory.preferences => 'Preferenze',
    JackCoreCategory.events => 'Eventi',
    JackCoreCategory.other => 'Altro',
  };

  String _sourceTypeLabel(JackCoreSourceType sourceType) =>
      switch (sourceType) {
        JackCoreSourceType.saved => 'Memoria salvata',
        JackCoreSourceType.retrieved => 'Informazione recuperata',
        JackCoreSourceType.inference => 'Inferenza',
      };

  String _verificationLabel(JackCoreVerification verification) =>
      switch (verification) {
        JackCoreVerification.verified => 'Verificata',
        JackCoreVerification.toVerify => 'Da verificare',
        JackCoreVerification.inferred => 'Inferita',
      };

  String _available(String value) =>
      value.trim().isEmpty ? 'Non disponibile' : value;

  String _lastUsedLabel(BuildContext context, DateTime? lastUsed) {
    if (lastUsed == null) return 'Non disponibile';
    final local = lastUsed.toLocal();
    final date = MaterialLocalizations.of(context).formatMediumDate(local);
    final time = MaterialLocalizations.of(context)
        .formatTimeOfDay(TimeOfDay.fromDateTime(local));
    return '$date · $time';
  }
}

class _EmptyNodePreview extends StatelessWidget {
  const _EmptyNodePreview();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 18),
      decoration: BoxDecoration(
        color: const Color(0xFF1D2023),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF303236)),
      ),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.hub_outlined, color: Color(0xFFC69A51), size: 19),
          SizedBox(height: 10),
          Text(
            'Nessun nodo selezionato',
            style: TextStyle(
              color: Color(0xFFE0DDD7),
              fontSize: 13,
              fontWeight: FontWeight.w500,
            ),
          ),
          SizedBox(height: 5),
          Text(
            'Seleziona un nodo nel nucleo per consultarne i dettagli.',
            style: TextStyle(
              color: Color(0xFF9A9A9B),
              fontSize: 11,
              height: 1.45,
            ),
          ),
        ],
      ),
    );
  }
}

class _MetadataRow extends StatelessWidget {
  const _MetadataRow({
    required this.label,
    required this.value,
    this.valueColor,
  });

  final String label;
  final String value;
  final Color? valueColor;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 82,
            child: Text(
              label,
              style: const TextStyle(color: Color(0xFF8F9091), fontSize: 10),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                color: valueColor ?? const Color(0xFFD0CECA),
                fontSize: 11,
                height: 1.35,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionHeading extends StatelessWidget {
  const _SectionHeading(this.text);

  final String text;

  @override
  Widget build(BuildContext context) => Text(
    text,
    style: const TextStyle(
      color: Color(0xFFB9B8B5),
      fontSize: 10,
      letterSpacing: 0.5,
      fontWeight: FontWeight.w600,
    ),
  );
}

class _TagPill extends StatelessWidget {
  const _TagPill({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: const Color(0xFF242629),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: const Color(0xFF383A3D)),
      ),
      child: Text(
        label,
        style: const TextStyle(color: Color(0xFFBDBBB7), fontSize: 10),
      ),
    );
  }
}

class _RelationRow extends StatelessWidget {
  const _RelationRow({
    required this.edge,
    required this.selectedNode,
    required this.graph,
  });

  final JackCoreEdge edge;
  final JackCoreNode selectedNode;
  final JackCoreGraph graph;

  @override
  Widget build(BuildContext context) {
    final relatedId = edge.fromId == selectedNode.id ? edge.toId : edge.fromId;
    final relatedNode = graph.nodes.where((node) => node.id == relatedId);
    final title = relatedNode.isEmpty
        ? 'Non disponibile'
        : relatedNode.first.title;
    return Padding(
      padding: const EdgeInsets.only(bottom: 7),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.only(top: 4),
            child: Icon(
              Icons.more_horiz_rounded,
              size: 14,
              color: Color(0xFF71BFC4),
            ),
          ),
          const SizedBox(width: 7),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: Color(0xFFD0CECA),
                    fontSize: 10,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  '${edge.relation} · forza ${edge.strength}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: Color(0xFF8F9091), fontSize: 9),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

