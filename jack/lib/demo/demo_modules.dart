/// Catalog of J.A.C.K. capabilities shown in the Moduli screen.
///
/// This is not demonstration data: it describes the real state of the 2.0
/// roadmap. Active modules exist in the current build; planned modules state
/// the milestone in which they become available.
library;

import 'package:flutter/material.dart';

import '../design_system/jack_tone.dart';
import '../navigation/jack_destination.dart';

enum DemoModuleCategory {
  interface('Interfaccia'),
  data('Dati'),
  ai('AI'),
  agents('Agenti'),
  system('Sistema'),
  security('Sicurezza');

  const DemoModuleCategory(this.label);

  final String label;
}

enum DemoModuleStatus {
  active('Attivo', JackTone.success),
  planned('Pianificato', JackTone.neutral);

  const DemoModuleStatus(this.label, this.tone);

  final String label;
  final JackTone tone;
}

class DemoModule {
  const DemoModule({
    required this.id,
    required this.name,
    required this.description,
    required this.category,
    required this.status,
    required this.milestone,
    required this.icon,
    required this.capabilities,
    this.destination,
  });

  final String id;
  final String name;
  final String description;
  final DemoModuleCategory category;
  final DemoModuleStatus status;
  final String milestone;
  final IconData icon;
  final List<String> capabilities;
  final JackDestination? destination;

  bool get isActive => status == DemoModuleStatus.active;
}

const List<DemoModule> demoModules = <DemoModule>[
  DemoModule(
    id: 'interface',
    name: 'Interfaccia desktop',
    description: 'Shell adattiva con sidebar, top bar contestuale, area centrale e pannelli laterali.',
    category: DemoModuleCategory.interface,
    status: DemoModuleStatus.active,
    milestone: 'M2',
    icon: Icons.desktop_windows_outlined,
    capabilities: <String>['Layout adattivo', 'Navigazione', 'Pannelli'],
    destination: JackDestination.conversations,
  ),
  DemoModule(
    id: 'design-system',
    name: 'Design system',
    description: 'Token centralizzati e componenti condivisi per colori, tipografia, superfici, controlli e movimento.',
    category: DemoModuleCategory.interface,
    status: DemoModuleStatus.active,
    milestone: 'M2',
    icon: Icons.palette_outlined,
    capabilities: <String>['Token', 'Componenti', 'Accessibilità'],
  ),
  DemoModule(
    id: 'preferences',
    name: 'Preferenze e accessibilità',
    description: 'Preferenze locali persistenti, incluse la riduzione del movimento e l’identità del profilo.',
    category: DemoModuleCategory.interface,
    status: DemoModuleStatus.active,
    milestone: 'M2',
    icon: Icons.accessibility_new_outlined,
    capabilities: <String>['Movimento ridotto', 'Profilo locale'],
    destination: JackDestination.settings,
  ),
  DemoModule(
    id: 'memory-engine',
    name: 'Memory Engine',
    description: 'Memoria persistente con CRUD, ricerca, categorie, provenienza, verifica e knowledge graph.',
    category: DemoModuleCategory.data,
    status: DemoModuleStatus.planned,
    milestone: 'M3',
    icon: Icons.hub_outlined,
    capabilities: <String>['CRUD', 'Ricerca', 'Knowledge graph', 'Backup'],
    destination: JackDestination.memory,
  ),
  DemoModule(
    id: 'jack-core',
    name: 'JackCore e Knowledge Graph',
    description: 'Canvas 2D con gusci sferici, nodi, archi, orbite e dieci stati cognitivi collegati a eventi reali.',
    category: DemoModuleCategory.interface,
    status: DemoModuleStatus.planned,
    milestone: 'M4',
    icon: Icons.blur_on_outlined,
    capabilities: <String>['Canvas 2D', 'Dieci stati', 'Grafo reale'],
    destination: JackDestination.exploration,
  ),
  DemoModule(
    id: 'planning',
    name: 'Pianificazione operativa',
    description: 'Task, progetti, checklist, dipendenze, ricorrenze e calendario con persistenza locale.',
    category: DemoModuleCategory.data,
    status: DemoModuleStatus.planned,
    milestone: 'M3',
    icon: Icons.event_note_outlined,
    capabilities: <String>['Task', 'Progetti', 'Calendario', 'Dipendenze'],
    destination: JackDestination.planning,
  ),
  DemoModule(
    id: 'ai-hub',
    name: 'AI Hub',
    description: 'Provider multi-modello, credenziali nel Keychain, routing con failover, timeout e Cost Guard.',
    category: DemoModuleCategory.ai,
    status: DemoModuleStatus.planned,
    milestone: 'M5',
    icon: Icons.psychology_outlined,
    capabilities: <String>['Provider', 'Modelli', 'Routing', 'Cost Guard'],
    destination: JackDestination.aiHub,
  ),
  DemoModule(
    id: 'agency-catalog',
    name: 'Catalogo Agency',
    description: 'Import completo del catalogo upstream, divisioni, competenze, ricerca e indice aggiornabile.',
    category: DemoModuleCategory.agents,
    status: DemoModuleStatus.planned,
    milestone: 'M6',
    icon: Icons.groups_2_outlined,
    capabilities: <String>['272 profili', '20 divisioni', 'Ricerca'],
    destination: JackDestination.agency,
  ),
  DemoModule(
    id: 'agent-runtime',
    name: 'Agent Runtime',
    description: 'Esecuzione controllata degli agenti con strumenti autorizzati, tracce, valutazione e approvazioni.',
    category: DemoModuleCategory.agents,
    status: DemoModuleStatus.planned,
    milestone: 'M7',
    icon: Icons.play_circle_outline_rounded,
    capabilities: <String>['Runtime', 'Strumenti', 'Tracce', 'Valutazione'],
    destination: JackDestination.agency,
  ),
  DemoModule(
    id: 'conversation-engine',
    name: 'Conversation Engine',
    description: 'Pipeline cognitiva completa: comprensione, recupero memoria, pianificazione, esecuzione e risposta.',
    category: DemoModuleCategory.ai,
    status: DemoModuleStatus.planned,
    milestone: 'M8',
    icon: Icons.forum_outlined,
    capabilities: <String>['Pipeline', 'Contesto', 'Risposte reali'],
    destination: JackDestination.conversations,
  ),
  DemoModule(
    id: 'permissions',
    name: 'Permessi e approvazioni',
    description: 'Modello fail-closed: nessuna azione sensibile senza autorizzazione esplicita e tracciata.',
    category: DemoModuleCategory.security,
    status: DemoModuleStatus.planned,
    milestone: 'M7',
    icon: Icons.verified_user_outlined,
    capabilities: <String>['Fail-closed', 'Approvazioni', 'Audit'],
    destination: JackDestination.settings,
  ),
  DemoModule(
    id: 'system-monitor',
    name: 'Diagnostica di sistema',
    description: 'Stato di backend, database, provider e servizi con verifiche reali e cronologia delle attività.',
    category: DemoModuleCategory.system,
    status: DemoModuleStatus.planned,
    milestone: 'M9',
    icon: Icons.monitor_heart_outlined,
    capabilities: <String>['Health check', 'Database', 'Log'],
    destination: JackDestination.systemStatus,
  ),
  DemoModule(
    id: 'backup',
    name: 'Backup e ripristino',
    description: 'Snapshot coerenti dei database, validazione dei backup e ripristino con conferma esplicita.',
    category: DemoModuleCategory.system,
    status: DemoModuleStatus.planned,
    milestone: 'M9',
    icon: Icons.archive_outlined,
    capabilities: <String>['Snapshot', 'Validazione', 'Ripristino'],
    destination: JackDestination.systemStatus,
  ),
  DemoModule(
    id: 'import-export',
    name: 'Import ed export',
    description: 'Esportazione e importazione controllata di memorie, conversazioni e configurazioni locali.',
    category: DemoModuleCategory.data,
    status: DemoModuleStatus.planned,
    milestone: 'M9',
    icon: Icons.swap_vert_rounded,
    capabilities: <String>['Export', 'Import', 'Verifica'],
    destination: JackDestination.settings,
  ),
];
