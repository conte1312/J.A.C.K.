import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:jack/app.dart';
import 'package:jack/models/planning.dart';
import 'package:jack/services/backend_status_service.dart';
import 'package:jack/services/planning_api_service.dart';

void main() {
  testWidgets('sidebar opens planning with real-data empty states', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      JackApp(
        backendStatusReader: _OfflineBackendReader(),
        planningGateway: _EmptyPlanningGateway(),
      ),
    );
    await tester.pump();
    await tester.tap(find.text('Pianificazione').first);
    await tester.pump();
    await tester.pump();

    expect(find.text('Dai forma alla giornata.'), findsOneWidget);
    expect(find.text('La giornata è libera'), findsOneWidget);
    expect(find.text('Nessun appuntamento'), findsOneWidget);
    expect(find.text('DATI DEMO'), findsNothing);

    await tester.tap(find.text('Missioni'));
    await tester.pump();
    await tester.pump();
    expect(find.text('Nessuna missione pianificata'), findsOneWidget);
  });

  testWidgets('creates a persisted planned mission from its form', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final gateway = _EmptyPlanningGateway();
    await tester.pumpWidget(
      JackApp(
        backendStatusReader: _OfflineBackendReader(),
        planningGateway: gateway,
      ),
    );
    await tester.pump();
    await tester.tap(find.text('Pianificazione').first);
    await tester.pump();
    await tester.pump();
    await tester.tap(find.text('Missioni'));
    await tester.pump();
    await tester.pump();
    await tester.tap(find.text('Nuova missione'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.widgetWithText(TextField, 'Obiettivo *'),
      'Preparare il rilascio',
    );
    await tester.tap(find.text('Salva'));
    await tester.pumpAndSettle();

    expect(gateway.missions.single.title, 'Preparare il rilascio');
    expect(find.text('Preparare il rilascio'), findsOneWidget);
  });

  testWidgets('creates task and project from their planning forms', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final gateway = _EmptyPlanningGateway();
    await tester.pumpWidget(
      JackApp(
        backendStatusReader: _OfflineBackendReader(),
        planningGateway: gateway,
      ),
    );
    await tester.pump();
    await tester.tap(find.text('Pianificazione').first);
    await tester.pump();
    await tester.pump();
    await tester.tap(find.text('Nuova attività'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.widgetWithText(TextField, 'Titolo *'),
      'Verificare il rilascio',
    );
    await tester.tap(find.text('Salva'));
    await tester.pumpAndSettle();
    expect(gateway.tasks.single.title, 'Verificare il rilascio');

    await tester.tap(find.text('Progetti'));
    await tester.pump();
    await tester.pump();
    await tester.tap(find.text('Crea progetto'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.widgetWithText(TextField, 'Nome *'),
      'Rilascio V1.2',
    );
    await tester.tap(find.text('Salva'));
    await tester.pumpAndSettle();

    expect(gateway.projects.single.name, 'Rilascio V1.2');
  });

  testWidgets('persists the selected default calendar timezone', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 1000);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    final gateway = _EmptyPlanningGateway();
    await tester.pumpWidget(
      JackApp(
        backendStatusReader: _OfflineBackendReader(),
        planningGateway: gateway,
      ),
    );
    await tester.pump();
    await tester.tap(find.text('Pianificazione').first);
    await tester.pump();
    await tester.pump();
    await tester.tap(find.byType(DropdownMenu<String>).first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Asia/Tokyo').last);
    await tester.pumpAndSettle();

    expect(gateway.defaultTimezone, 'Asia/Tokyo');
  });
}

class _OfflineBackendReader implements BackendStatusReader {
  @override
  Future<BackendSnapshot?> check() async => null;
}

class _EmptyPlanningGateway implements PlanningGateway {
  final List<PlanningTask> tasks = [];
  final List<PlanningProject> projects = [];
  final List<PlanningMission> missions = [];

  @override
  Future<List<PlanningTask>> listTasks({
    String? query,
    String? status,
    String? priority,
    String? projectId,
    String? missionId,
    String? category,
    String? tag,
    String? dueAfter,
    String? dueBefore,
    bool overdueOnly = false,
    String? sort,
    bool descending = false,
  }) async => List.unmodifiable(tasks);

  @override
  Future<List<PlanningProject>> listProjects({String? query}) async =>
      List.unmodifiable(projects);

  @override
  Future<PlanningTask> createTask(Map<String, Object?> draft) async {
    final task = PlanningTask(
      id: 'task-${tasks.length + 1}',
      title: draft['title']! as String,
      status: draft['status']! as String,
      priority: draft['priority']! as String,
      description: draft['description']! as String,
      category: draft['category']! as String,
      tags: draft['tags']! as List<String>,
      projectId: draft['project_id'] as String?,
      missionId: draft['mission_id'] as String?,
      startDate: draft['start_date'] as String?,
      dueDate: draft['due_date'] as String?,
      recurrenceKind: draft['recurrence_kind']! as String,
      recurrenceInterval: draft['recurrence_interval']! as int,
      responsibleAgent: draft['responsible_agent'] as String?,
      notes: draft['notes']! as String,
    );
    tasks.add(task);
    return task;
  }

  @override
  Future<PlanningProject> createProject(Map<String, Object?> draft) async {
    final project = PlanningProject(
      id: 'project-${projects.length + 1}',
      name: draft['name']! as String,
      description: draft['description']! as String,
      goal: draft['goal']! as String,
      status: draft['status']! as String,
      priority: draft['priority']! as String,
      startDate: draft['start_date'] as String?,
      dueDate: draft['due_date'] as String?,
      notes: draft['notes']! as String,
      completionPercent: 0,
      openTaskCount: 0,
      completedTaskCount: 0,
    );
    projects.add(project);
    return project;
  }

  @override
  Future<List<PlanningMission>> listMissions({String? status}) async =>
      List.unmodifiable(missions);

  @override
  Future<PlanningMission> createMission(Map<String, Object?> draft) async {
    final mission = PlanningMission(
      id: 'mission-${missions.length + 1}',
      title: draft['title']! as String,
      status: draft['status']! as String,
      progressPercent: 0,
      description: draft['description']! as String,
      plan: draft['plan']! as String,
      assignedAgents: draft['assigned_agents']! as List<String>,
      results: draft['results']! as String,
      notes: draft['notes']! as String,
    );
    missions.add(mission);
    return mission;
  }

  @override
  Future<PlanningCalendar> getCalendar({
    required DateTime from,
    required DateTime to,
    required String timezone,
    String? projectId,
    String? priority,
  }) async =>
      PlanningCalendar(tasks: const [], events: const [], timezone: timezone);

  @override
  Future<List<String>> listTimezones() async => const [
    'America/New_York',
    'Asia/Tokyo',
    'Europe/Rome',
    'UTC',
  ];

  String defaultTimezone = 'Europe/Rome';

  @override
  Future<String> getDefaultTimezone() async => defaultTimezone;

  @override
  Future<String> setDefaultTimezone(String timezone) async =>
      defaultTimezone = timezone;

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
