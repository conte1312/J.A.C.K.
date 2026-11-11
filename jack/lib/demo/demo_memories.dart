/// Demonstration memories for the M2 interface.
///
/// No memory is stored in SQLite and no Memory Engine is running yet.
/// The real archive arrives with M3.
library;

enum DemoMemoryCategory {
  identity('Identità'),
  work('Lavoro'),
  projects('Progetti'),
  people('Persone'),
  technical('Tecnica'),
  preferences('Preferenze'),
  events('Eventi'),
  other('Altro');

  const DemoMemoryCategory(this.label);

  final String label;
}

class DemoMemory {
  const DemoMemory({
    required this.id,
    required this.title,
    required this.content,
    required this.category,
    required this.tags,
    required this.importance,
    required this.source,
    required this.verification,
    required this.updatedLabel,
  });

  final String id;
  final String title;
  final String content;
  final DemoMemoryCategory category;
  final List<String> tags;
  final int importance;
  final String source;
  final String verification;
  final String updatedLabel;
}

const List<DemoMemory> demoMemories = <DemoMemory>[
  DemoMemory(
    id: 'demo-identity',
    title: 'Identità visiva di J.A.C.K.',
    content: 'J.A.C.K. usa superfici grafite quasi nere, un accento ambra/oro e un accento secondario cyan. I bordi sono sottili, le superfici leggermente traslucide e le animazioni discrete. L’estetica deve risultare premium e nativa su macOS, non una dashboard amministrativa.',
    category: DemoMemoryCategory.identity,
    tags: <String>['brand', 'design', 'macos'],
    importance: 5,
    source: 'Aggiunto manualmente (demo)',
    verification: 'Verificato',
    updatedLabel: 'Oggi',
  ),
  DemoMemory(
    id: 'demo-preference-concise',
    title: 'Preferenza: risposte concise',
    content: 'L’utente preferisce risposte dirette, con struttura chiara e senza ripetizioni. Quando serve una spiegazione lunga, è meglio separarla in sezioni brevi e citare le decisioni prese.',
    category: DemoMemoryCategory.preferences,
    tags: <String>['stile', 'comunicazione'],
    importance: 5,
    source: 'Conversazione demo',
    verification: 'Verificato',
    updatedLabel: 'Oggi',
  ),
  DemoMemory(
    id: 'demo-project-jack',
    title: 'Progetto J.A.C.K. 2.0',
    content: 'Ricostruzione completa di J.A.C.K. con frontend Flutter, backend FastAPI locale e SQLite. Lo sviluppo procede per milestone approvate: fondazioni, design system, Memory Engine, JackCore, AI Hub, catalogo Agency, runtime agenti, Conversation Engine e integrazione finale.',
    category: DemoMemoryCategory.projects,
    tags: <String>['flutter', 'fastapi', 'sqlite'],
    importance: 5,
    source: 'Aggiunto manualmente (demo)',
    verification: 'Verificato',
    updatedLabel: 'Oggi',
  ),
  DemoMemory(
    id: 'demo-stack',
    title: 'Stack tecnico del progetto',
    content: 'Flutter e Dart per l’interfaccia desktop, Python e FastAPI per il backend locale vincolato a 127.0.0.1, SQLite con repository pattern e migrazioni versionate. Nessun microservizio e nessuna dipendenza non necessaria.',
    category: DemoMemoryCategory.technical,
    tags: <String>['dart', 'python', 'architettura'],
    importance: 4,
    source: 'Aggiunto manualmente (demo)',
    verification: 'Verificato',
    updatedLabel: 'Ieri',
  ),
  DemoMemory(
    id: 'demo-m2-goal',
    title: 'Obiettivo della milestone M2',
    content: 'Realizzare il design system definitivo e le dieci schermate navigabili, con layout adattivo, stati di caricamento, vuoto ed errore, componenti condivisi e test. I servizi delle milestone successive restano esplicitamente non disponibili.',
    category: DemoMemoryCategory.work,
    tags: <String>['design system', 'ui', 'test'],
    importance: 4,
    source: 'Conversazione demo',
    verification: 'Verificato',
    updatedLabel: 'Ieri',
  ),
  DemoMemory(
    id: 'demo-agency-divisions',
    title: 'Divisioni del catalogo Agency',
    content: 'Il catalogo upstream agency-agents contiene 272 profili in 20 divisioni, tra cui engineering, design, product, marketing, project management, testing, support, sales, finance, security, specialized e spatial computing. L’import completo avviene in M6.',
    category: DemoMemoryCategory.technical,
    tags: <String>['agency', 'catalogo', 'agent'],
    importance: 3,
    source: 'Aggiunto manualmente (demo)',
    verification: 'Da verificare',
    updatedLabel: '6 nov',
  ),
  DemoMemory(
    id: 'demo-friday-routine',
    title: 'Routine del venerdì',
    content: 'Il venerdì pomeriggio è dedicato alla rassegna settimanale: riepilogo delle attività completate, verifica delle dipendenze aperte e pianificazione della settimana successiva. Le riunioni lunghe vanno evitate.',
    category: DemoMemoryCategory.events,
    tags: <String>['pianificazione', 'routine'],
    importance: 3,
    source: 'Conversazione demo',
    verification: 'Verificato',
    updatedLabel: '6 nov',
  ),
  DemoMemory(
    id: 'demo-team',
    title: 'Team di sviluppo',
    content: 'Il team preferisce revisioni brevi e frequenti, con cambiamenti di piccole dimensioni e documentazione aggiornata insieme al codice. Le decisioni architetturali vengono registrate prima dell’implementazione.',
    category: DemoMemoryCategory.people,
    tags: <String>['team', 'collaborazione'],
    importance: 3,
    source: 'Aggiunto manualmente (demo)',
    verification: 'Da verificare',
    updatedLabel: '4 nov',
  ),
];
