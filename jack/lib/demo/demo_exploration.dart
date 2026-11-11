/// Demonstration knowledge graph for the M2 interface.
///
/// Nodes and edges are presentation-only. Real graph data arrives with the
/// Memory Engine (M3); the interactive JackCore visual arrives with M4.
library;

import '../design_system/jack_tone.dart';

enum DemoGraphCategory {
  identity('Identità', JackTone.cyan),
  projects('Progetti', JackTone.amber),
  technical('Tecnica', JackTone.info),
  preferences('Preferenze', JackTone.success),
  events('Eventi', JackTone.warning);

  const DemoGraphCategory(this.label, this.tone);

  final String label;
  final JackTone tone;
}

class DemoGraphNode {
  const DemoGraphNode({
    required this.id,
    required this.label,
    required this.category,
    required this.description,
    required this.connections,
  });

  final String id;
  final String label;
  final DemoGraphCategory category;
  final String description;
  final List<String> connections;
}

const List<DemoGraphNode> demoGraphNodes = <DemoGraphNode>[
  DemoGraphNode(
    id: 'jack-2',
    label: 'J.A.C.K. 2.0',
    category: DemoGraphCategory.projects,
    description: 'Ricostruzione completa dell’app: interfaccia Flutter, backend FastAPI locale e database SQLite per dominio.',
    connections: <String>[
      'memory-engine',
      'design-system',
      'ai-hub',
      'agency',
      'milestone-m2',
    ],
  ),
  DemoGraphNode(
    id: 'memory-engine',
    label: 'Memory Engine',
    category: DemoGraphCategory.projects,
    description: 'Motore della memoria persistente: CRUD, ricerca, categorie, provenienza, verifica e proposte soggette ad approvazione.',
    connections: <String>['jack-2', 'knowledge-graph', 'sqlite'],
  ),
  DemoGraphNode(
    id: 'knowledge-graph',
    label: 'Knowledge Graph',
    category: DemoGraphCategory.technical,
    description: 'Rappresentazione dei collegamenti tra ricordi, con relazione e forza del legame. Alimenta l’Esplorazione.',
    connections: <String>['memory-engine', 'exploration'],
  ),
  DemoGraphNode(
    id: 'design-system',
    label: 'Design System',
    category: DemoGraphCategory.projects,
    description: 'Token e componenti condivisi: colori, tipografia, spaziature, radius, bordi, ombre, movimento e controlli interattivi.',
    connections: <String>['jack-2', 'jack-core', 'reduced-motion'],
  ),
  DemoGraphNode(
    id: 'jack-core',
    label: 'JackCore',
    category: DemoGraphCategory.projects,
    description: 'Componente Canvas 2D con gusci sferici, nodi, archi e dieci stati cognitivi. Attivazione prevista in M4.',
    connections: <String>['design-system', 'exploration'],
  ),
  DemoGraphNode(
    id: 'ai-hub',
    label: 'AI Hub',
    category: DemoGraphCategory.projects,
    description: 'Registro provider, modelli, credenziali nel Keychain, routing con failover e Cost Guard sui modelli gratuiti.',
    connections: <String>['jack-2', 'providers'],
  ),
  DemoGraphNode(
    id: 'providers',
    label: 'Provider AI',
    category: DemoGraphCategory.technical,
    description: 'NVIDIA NIM, Google Gemini, GroqCloud, OpenRouter e Ollama. Nessun provider è configurato in M2.',
    connections: <String>['ai-hub'],
  ),
  DemoGraphNode(
    id: 'agency',
    label: 'Agency',
    category: DemoGraphCategory.projects,
    description: 'Catalogo completo dei profili agency-agents, divisioni, competenze e composizione del team. Import in M6.',
    connections: <String>['jack-2', 'agent-runtime'],
  ),
  DemoGraphNode(
    id: 'agent-runtime',
    label: 'Agent Runtime',
    category: DemoGraphCategory.technical,
    description: 'Esecuzione controllata degli agenti con strumenti autorizzati, tracce, valutazione e approvazioni. Previsto in M7.',
    connections: <String>['agency', 'permissions'],
  ),
  DemoGraphNode(
    id: 'permissions',
    label: 'Permessi e approvazioni',
    category: DemoGraphCategory.preferences,
    description: 'Modello fail-closed: nessuna azione sensibile senza autorizzazione esplicita. Nessuna esecuzione autonoma.',
    connections: <String>['agent-runtime'],
  ),
  DemoGraphNode(
    id: 'reduced-motion',
    label: 'Movimento ridotto',
    category: DemoGraphCategory.preferences,
    description: 'Preferenza locale e di sistema che riduce le animazioni non essenziali in tutta l’applicazione.',
    connections: <String>['design-system'],
  ),
  DemoGraphNode(
    id: 'milestone-m2',
    label: 'Milestone M2',
    category: DemoGraphCategory.events,
    description: 'Design system definitivo e dieci schermate navigabili. I servizi non ancora disponibili sono dichiarati esplicitamente.',
    connections: <String>['jack-2', 'design-system'],
  ),
  DemoGraphNode(
    id: 'exploration',
    label: 'Esplorazione',
    category: DemoGraphCategory.events,
    description: 'Vista del grafo con filtri, legenda, controlli di visualizzazione e pannello dettagli.',
    connections: <String>['knowledge-graph', 'jack-core'],
  ),
  DemoGraphNode(
    id: 'sqlite',
    label: 'SQLite',
    category: DemoGraphCategory.technical,
    description: 'Database locale con migrazioni versionate e repository indipendenti per dominio.',
    connections: <String>['memory-engine'],
  ),
];
