enum JackCoreGraphOrigin { demo, live }

/// A rendering layer only. It does not encode category, importance, or trust.
enum JackCoreShell { surface, interior }

enum JackCoreCategory {
  identity,
  work,
  projects,
  people,
  technical,
  preferences,
  events,
  other,
}

enum JackCoreSourceType { saved, retrieved, inference }

enum JackCoreVerification { verified, toVerify, inferred }

class JackCoreNode {
  const JackCoreNode({
    required this.id,
    required this.title,
    required this.category,
    required this.sourceType,
    required this.source,
    required this.verification,
    this.content = '',
    this.tags = const [],
    this.importance = 3,
    this.excluded = false,
    this.conversationId,
    this.lastUsed,
    this.shell = JackCoreShell.surface,
  }) : assert(importance >= 1 && importance <= 5);

  final String id;
  final String title;
  final String content;
  final JackCoreCategory category;
  final JackCoreSourceType sourceType;
  final String source;
  final JackCoreVerification verification;
  final List<String> tags;
  final int importance;
  final bool excluded;
  final String? conversationId;
  final DateTime? lastUsed;

  /// Stable visual placement, independent of all semantic node attributes.
  final JackCoreShell shell;
}

class JackCoreEdge {
  const JackCoreEdge({
    required this.id,
    required this.fromId,
    required this.toId,
    required this.relation,
    this.strength = 1,
  }) : assert(strength >= 1 && strength <= 3);

  final String id;
  final String fromId;
  final String toId;
  final String relation;
  final int strength;
}

class JackCoreGraph {
  const JackCoreGraph({
    required this.nodes,
    required this.edges,
    required this.origin,
  });

  final List<JackCoreNode> nodes;
  final List<JackCoreEdge> edges;
  final JackCoreGraphOrigin origin;

  /// Grafico vuoto: stato reale quando non ci sono ricordi. Sostituisce il
  /// fallback dati-demo, così il Knowledge Core mostra solo informazioni vere.
  static const JackCoreGraph empty = JackCoreGraph(
    nodes: [],
    edges: [],
    origin: JackCoreGraphOrigin.live,
  );

  String? validate() {
    final ids = nodes.map((node) => node.id).toSet();
    if (ids.length != nodes.length) {
      return 'Gli ID dei nodi devono essere univoci.';
    }
    final edgeIds = edges.map((edge) => edge.id).toSet();
    if (edgeIds.length != edges.length) {
      return 'Gli ID degli archi devono essere univoci.';
    }
    for (final edge in edges) {
      if (!ids.contains(edge.fromId) || !ids.contains(edge.toId)) {
        return 'Un arco fa riferimento a un nodo assente.';
      }
      if (edge.fromId == edge.toId) {
        return 'Un arco non può collegare un nodo a sé stesso.';
      }
    }
    return null;
  }
}
