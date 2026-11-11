/// Demonstration planning data for the M2 interface.
///
/// Tasks, projects and calendar events are presentation-only. They are not
/// persisted and no planning engine is running yet.
library;

import '../design_system/jack_tone.dart';

enum DemoTaskStatus {
  todo('Da fare', JackTone.neutral),
  inProgress('In corso', JackTone.cyan),
  done('Completate', JackTone.success);

  const DemoTaskStatus(this.label, this.tone);

  final String label;
  final JackTone tone;
}

enum DemoPriority {
  low('Bassa', JackTone.neutral),
  medium('Media', JackTone.amber),
  high('Alta', JackTone.error);

  const DemoPriority(this.label, this.tone);

  final String label;
  final JackTone tone;
}

class DemoChecklistItem {
  const DemoChecklistItem({required this.label, required this.done});

  final String label;
  final bool done;
}

class DemoTask {
  const DemoTask({
    required this.id,
    required this.title,
    required this.description,
    required this.status,
    required this.priority,
    required this.dueDate,
    required this.project,
    required this.tags,
    this.checklist = const <DemoChecklistItem>[],
    this.dependencies = const <String>[],
  });

  final String id;
  final String title;
  final String description;
  final DemoTaskStatus status;
  final DemoPriority priority;
  final DateTime dueDate;
  final String project;
  final List<String> tags;
  final List<DemoChecklistItem> checklist;
  final List<String> dependencies;

  DemoTask copyWith({DemoTaskStatus? status}) {
    return DemoTask(
      id: id,
      title: title,
      description: description,
      status: status ?? this.status,
      priority: priority,
      dueDate: dueDate,
      project: project,
      tags: tags,
      checklist: checklist,
      dependencies: dependencies,
    );
  }
}

class DemoProjectMilestone {
  const DemoProjectMilestone({required this.label, required this.state});

  final String label;
  final String state;
}

class DemoProject {
  const DemoProject({
    required this.id,
    required this.name,
    required this.description,
    required this.progress,
    required this.taskCount,
    required this.dueDate,
    required this.status,
    required this.milestones,
  });

  final String id;
  final String name;
  final String description;
  final double progress;
  final int taskCount;
  final DateTime dueDate;
  final String status;
  final List<DemoProjectMilestone> milestones;
}

final List<DemoTask> demoTasks = <DemoTask>[
  DemoTask(
    id: 'task-tokens',
    title: 'Definire i token del design system',
    description: 'Colori, tipografia, spaziature, radius, bordi, ombre, superfici e movimento centralizzati in un unico layer.',
    status: DemoTaskStatus.done,
    priority: DemoPriority.high,
    dueDate: DateTime(2026, 11, 8),
    project: 'Design System',
    tags: <String>['token', 'ui'],
    checklist: <DemoChecklistItem>[
      DemoChecklistItem(label: 'Palette e contrasto', done: true),
      DemoChecklistItem(label: 'Tipografia e spaziature', done: true),
      DemoChecklistItem(label: 'Breakpoint adattivi', done: true),
    ],
  ),
  DemoTask(
    id: 'task-screens',
    title: 'Completare le dieci schermate',
    description: 'Ogni schermata deve essere navigabile, adattiva e onesta rispetto ai servizi non ancora disponibili.',
    status: DemoTaskStatus.inProgress,
    priority: DemoPriority.high,
    dueDate: DateTime(2026, 11, 10),
    project: 'J.A.C.K. 2.0',
    tags: <String>['ui', 'milestone-m2'],
    checklist: <DemoChecklistItem>[
      DemoChecklistItem(label: 'Schermate principali', done: true),
      DemoChecklistItem(label: 'Pannelli laterali', done: false),
      DemoChecklistItem(label: 'Stati vuoti e non disponibili', done: false),
    ],
    dependencies: <String>['task-tokens'],
  ),
  DemoTask(
    id: 'task-adaptive-tests',
    title: 'Test di navigazione adattiva',
    description: 'Verificare sidebar espansa, rail compatta e drawer per finestre strette, senza perdita di stato.',
    status: DemoTaskStatus.inProgress,
    priority: DemoPriority.medium,
    dueDate: DateTime(2026, 11, 12),
    project: 'J.A.C.K. 2.0',
    tags: <String>['test', 'responsive'],
    dependencies: <String>['task-screens'],
  ),
  DemoTask(
    id: 'task-palette-review',
    title: 'Rivedere la palette ambra/cyan',
    description: 'Controllare il contrasto dei testi secondari e l’uso dell’accento cyan nelle superfici grafite.',
    status: DemoTaskStatus.done,
    priority: DemoPriority.medium,
    dueDate: DateTime(2026, 11, 6),
    project: 'Design System',
    tags: <String>['colore', 'accessibilità'],
  ),
  DemoTask(
    id: 'task-agency-import',
    title: 'Preparare l’import del catalogo Agency',
    description: 'Congelare il commit upstream, verificare licenza e attribuzioni e predisporre l’indice ricercabile.',
    status: DemoTaskStatus.todo,
    priority: DemoPriority.high,
    dueDate: DateTime(2026, 11, 14),
    project: 'Catalogo Agency',
    tags: <String>['agency', 'catalogo'],
  ),
  DemoTask(
    id: 'task-limitations',
    title: 'Documentare le limitazioni M2',
    description: 'Elencare ciò che è reale, ciò che è dimostrativo e la milestone in cui ogni servizio diventerà operativo.',
    status: DemoTaskStatus.todo,
    priority: DemoPriority.medium,
    dueDate: DateTime(2026, 11, 18),
    project: 'J.A.C.K. 2.0',
    tags: <String>['documentazione'],
  ),
  DemoTask(
    id: 'task-macos-build',
    title: 'Verifica build macOS',
    description: 'Eseguire format, analyze, test e build release dell’app macOS senza errori bloccanti.',
    status: DemoTaskStatus.todo,
    priority: DemoPriority.high,
    dueDate: DateTime(2026, 11, 20),
    project: 'J.A.C.K. 2.0',
    tags: <String>['build', 'qualità'],
    dependencies: <String>['task-adaptive-tests'],
  ),
  DemoTask(
    id: 'task-memory-draft',
    title: 'Bozza del Memory Engine',
    description: 'Schema SQLite, repository, migrazioni versionate e API di lettura per la milestone M3.',
    status: DemoTaskStatus.todo,
    priority: DemoPriority.medium,
    dueDate: DateTime(2026, 11, 24),
    project: 'J.A.C.K. 2.0',
    tags: <String>['memory', 'backend'],
  ),
  DemoTask(
    id: 'task-weekly-review',
    title: 'Rassegna settimanale',
    description: 'Riepilogare le attività completate, le dipendenze aperte e le priorità della settimana successiva.',
    status: DemoTaskStatus.done,
    priority: DemoPriority.low,
    dueDate: DateTime(2026, 11, 7),
    project: 'Attività personali',
    tags: <String>['routine'],
  ),
  DemoTask(
    id: 'task-m3-planning',
    title: 'Pianificare la milestone M3',
    description: 'Definire perimetro, criteri di accettazione e test del Memory Engine prima di iniziare l’implementazione.',
    status: DemoTaskStatus.todo,
    priority: DemoPriority.high,
    dueDate: DateTime(2026, 11, 27),
    project: 'J.A.C.K. 2.0',
    tags: <String>['milestone', 'pianificazione'],
    dependencies: <String>['task-limitations'],
  ),
];

final List<DemoProject> demoProjects = <DemoProject>[
  DemoProject(
    id: 'project-jack',
    name: 'J.A.C.K. 2.0',
    description: 'Ricostruzione completa dell’app con milestone approvate e integrazione finale in main.',
    progress: 0.42,
    taskCount: 6,
    dueDate: DateTime(2026, 12, 20),
    status: 'In corso',
    milestones: <DemoProjectMilestone>[
      DemoProjectMilestone(label: 'M2 — Design system e UI', state: 'In corso'),
      DemoProjectMilestone(label: 'M3 — Memory Engine', state: 'Pianificata'),
      DemoProjectMilestone(label: 'M5 — AI Hub', state: 'Pianificata'),
    ],
  ),
  DemoProject(
    id: 'project-design-system',
    name: 'Design System',
    description: 'Token, componenti condivisi, accessibilità e movimento controllato per tutte le schermate.',
    progress: 0.86,
    taskCount: 3,
    dueDate: DateTime(2026, 11, 12),
    status: 'In corso',
    milestones: <DemoProjectMilestone>[
      DemoProjectMilestone(label: 'Token e palette', state: 'Completata'),
      DemoProjectMilestone(label: 'Componenti condivisi', state: 'Completata'),
      DemoProjectMilestone(label: 'Verifica accessibilità', state: 'In corso'),
    ],
  ),
  DemoProject(
    id: 'project-agency-catalog',
    name: 'Catalogo Agency',
    description: 'Import completo del catalogo upstream, indice ricercabile e adattamenti J.A.C.K. separati.',
    progress: 0.15,
    taskCount: 2,
    dueDate: DateTime(2026, 12, 5),
    status: 'Pianificato',
    milestones: <DemoProjectMilestone>[
      DemoProjectMilestone(label: 'Import completo', state: 'Pianificata'),
      DemoProjectMilestone(label: 'Runtime agenti', state: 'Pianificata'),
    ],
  ),
];
