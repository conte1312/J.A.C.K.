import 'dart:async';

import 'package:flutter/material.dart';

import '../models/planning.dart';
import '../services/local_api_client.dart';
import '../services/planning_api_service.dart';
import '../theme/jack_theme.dart';
import '../widgets/jack_primitives.dart';

enum _PlanningView { today, calendar, tasks, projects, missions }

enum _CalendarScale { day, week, month }

class PlanningScreen extends StatefulWidget {
  const PlanningScreen({required this.repository, this.onOpenChat, super.key});

  final PlanningGateway repository;
  final VoidCallback? onOpenChat;

  @override
  State<PlanningScreen> createState() => _PlanningScreenState();
}

class _PlanningScreenState extends State<PlanningScreen> {
  _PlanningView _view = _PlanningView.today;
  _CalendarScale _calendarScale = _CalendarScale.week;
  DateTime _selectedDate = DateUtils.dateOnly(DateTime.now());
  List<PlanningTask> _tasks = const [];
  List<PlanningProject> _projects = const [];
  List<PlanningMission> _missions = const [];
  PlanningCalendar? _calendar;
  String _query = '';
  String? _priority;
  String? _projectId;
  String? _statusFilter;
  String _sort = 'due_date';
  bool _sortDescending = false;
  bool _loading = true;
  bool _saving = false;
  String? _error;
  Timer? _searchTimer;
  String _timezone = 'Europe/Rome';
  List<String> _timezones = const ['Europe/Rome', 'UTC'];

  @override
  void initState() {
    super.initState();
    unawaited(_load());
  }

  @override
  void dispose() {
    _searchTimer?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    if (mounted) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    try {
      final timezones = await widget.repository.listTimezones();
      if (timezones.isEmpty) {
        throw const FormatException('Nessun fuso orario disponibile.');
      }
      final savedTimezone = await widget.repository.getDefaultTimezone();
      if (!timezones.contains(savedTimezone)) {
        throw const FormatException(
          'Il fuso orario predefinito non è disponibile nel catalogo IANA.',
        );
      }
      _timezone = savedTimezone;
      final range = _visibleRange;
      final results = await Future.wait<Object>([
        widget.repository.listTasks(
          query: _query,
          status: _statusFilter,
          priority: _priority,
          projectId: _projectId,
          sort: _sort,
          descending: _sortDescending,
        ),
        widget.repository.listProjects(query: _query),
        widget.repository.listMissions(),
        widget.repository.getCalendar(
          from: range.$1,
          to: range.$2,
          timezone: _timezone,
          projectId: _projectId,
          priority: _priority,
        ),
      ]);
      if (!mounted) return;
      setState(() {
        _timezones = timezones;
        _tasks = results[0] as List<PlanningTask>;
        _projects = results[1] as List<PlanningProject>;
        _missions = results[2] as List<PlanningMission>;
        _calendar = results[3] as PlanningCalendar;
        _loading = false;
      });
    } on LocalApiException catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        _loading = false;
      });
    } on Exception {
      if (!mounted) return;
      setState(() {
        _error = 'Impossibile caricare la pianificazione dal backend.';
        _loading = false;
      });
    }
  }

  (DateTime, DateTime) get _visibleRange {
    final selected = DateUtils.dateOnly(_selectedDate);
    if (_calendarScale == _CalendarScale.day) {
      return (selected, selected);
    }
    if (_calendarScale == _CalendarScale.week) {
      final start = selected.subtract(Duration(days: selected.weekday - 1));
      return (start, start.add(const Duration(days: 6)));
    }
    final start = DateTime(selected.year, selected.month);
    final end = DateTime(selected.year, selected.month + 1, 0);
    return (start, end);
  }

  List<PlanningEvent> get _visibleEvents => _calendar?.events ?? const [];

  Future<void> _run(Future<void> Function() action) async {
    if (_saving) return;
    setState(() => _saving = true);
    try {
      await action();
      await _load();
    } on LocalApiException catch (error) {
      if (!mounted) return;
      _showMessage(error.message, isError: true);
    } on Exception {
      if (!mounted) return;
      _showMessage(
        'Operazione non completata. I dati non sono stati aggiornati.',
        isError: true,
      );
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _changeTimezone(String timezone) async {
    if (_saving || timezone == _timezone) return;
    final previousTimezone = _timezone;
    setState(() {
      _timezone = timezone;
      _saving = true;
    });
    try {
      await widget.repository.setDefaultTimezone(timezone);
      await _load();
    } on LocalApiException catch (error) {
      if (!mounted) return;
      setState(() => _timezone = previousTimezone);
      _showMessage(error.message, isError: true);
    } on Exception {
      if (!mounted) return;
      setState(() => _timezone = previousTimezone);
      _showMessage('Preferenza del fuso orario non salvata.', isError: true);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _showMessage(String message, {bool isError = false}) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(message),
          backgroundColor: isError ? const Color(0xFF572D2B) : null,
        ),
      );
  }

  Future<void> _createTask({String? initialTitle}) async {
    final draft = await showDialog<Map<String, Object?>>(
      context: context,
      builder: (context) => _TaskEditorDialog(
        projects: _projects,
        missions: _missions,
        initialTitle: initialTitle,
      ),
    );
    if (draft == null) return;
    await _run(() async {
      await widget.repository.createTask(draft);
    });
  }

  Future<void> _editTask(PlanningTask task) async {
    final patch = await showDialog<Map<String, Object?>>(
      context: context,
      builder: (context) => _TaskEditorDialog(
        projects: _projects,
        missions: _missions,
        task: task,
      ),
    );
    if (patch == null) return;
    await _run(() async {
      await widget.repository.updateTask(task.id, patch);
    });
  }

  Future<void> _createProject() async {
    final draft = await showDialog<Map<String, Object?>>(
      context: context,
      builder: (context) => const _ProjectEditorDialog(),
    );
    if (draft == null) return;
    await _run(() async {
      await widget.repository.createProject(draft);
    });
  }

  Future<void> _createMission() async {
    final draft = await showDialog<Map<String, Object?>>(
      context: context,
      builder: (context) => const _MissionEditorDialog(),
    );
    if (draft == null) return;
    await _run(() async {
      await widget.repository.createMission(draft);
    });
  }

  Future<void> _editMission(PlanningMission mission) async {
    final patch = await showDialog<Map<String, Object?>>(
      context: context,
      builder: (context) => _MissionEditorDialog(mission: mission),
    );
    if (patch == null) return;
    await _run(() async {
      await widget.repository.updateMission(mission.id, patch);
    });
  }

  Future<void> _createMilestone(String projectId) async {
    final draft = await showDialog<Map<String, Object?>>(
      context: context,
      builder: (context) => const _MilestoneEditorDialog(),
    );
    if (draft == null) return;
    await _run(() async {
      await widget.repository.createMilestone(projectId, draft);
    });
  }

  Future<void> _editMilestone(ProjectMilestone milestone) async {
    final patch = await showDialog<Map<String, Object?>>(
      context: context,
      builder: (context) => _MilestoneEditorDialog(milestone: milestone),
    );
    if (patch == null) return;
    await _run(() async {
      await widget.repository.updateMilestone(milestone.id, patch);
    });
  }

  Future<void> _editProject(PlanningProject project) async {
    final patch = await showDialog<Map<String, Object?>>(
      context: context,
      builder: (context) => _ProjectEditorDialog(project: project),
    );
    if (patch == null) return;
    await _run(() async {
      await widget.repository.updateProject(project.id, patch);
    });
  }

  Future<void> _createEvent() async {
    final draft = await showDialog<Map<String, Object?>>(
      context: context,
      builder: (context) => _EventEditorDialog(
        projects: _projects,
        timezones: _timezones,
        initialTimezone: _timezone,
      ),
    );
    if (draft == null) return;
    await _run(() async {
      await widget.repository.createEvent(draft);
    });
  }

  Future<void> _editEvent(PlanningEvent event) async {
    final patch = await showDialog<Map<String, Object?>>(
      context: context,
      builder: (context) => _EventEditorDialog(
        projects: _projects,
        timezones: _timezones,
        initialTimezone: _timezone,
        event: event,
      ),
    );
    if (patch == null) return;
    await _run(() async {
      await widget.repository.updateEvent(event.id, patch);
    });
  }

  Future<void> _showTaskDetails(PlanningTask task) async {
    await showDialog<void>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          backgroundColor: JackPalette.panel,
          title: Text(task.title),
          content: SizedBox(
            width: 460,
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    task.description.isEmpty
                        ? 'Nessuna descrizione.'
                        : task.description,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    [
                      _statusLabel(task.status),
                      _priorityLabel(task.priority),
                      if (task.startDate != null) 'Inizio ${task.startDate}',
                      if (task.dueDate != null) 'Scadenza ${task.dueDate}',
                      if (task.completedAt != null)
                        'Completata ${task.completedAt}',
                      if (task.category.isNotEmpty) task.category,
                      if (task.responsibleAgent != null)
                        'Agente ${task.responsibleAgent}',
                    ].join(' · '),
                    style: const TextStyle(
                      color: JackPalette.muted,
                      fontSize: 11,
                    ),
                  ),
                  if (task.tags.isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Text(
                      task.tags.map((tag) => '#$tag').join('  '),
                      style: const TextStyle(
                        color: JackPalette.cyan,
                        fontSize: 11,
                      ),
                    ),
                  ],
                  if (task.missionId != null) ...[
                    const SizedBox(height: 6),
                    Text(
                      'Missione: ${_missionTitle(task.missionId!)}',
                      style: const TextStyle(
                        color: JackPalette.amber,
                        fontSize: 11,
                      ),
                    ),
                  ],
                  const SizedBox(height: 16),
                  const SectionEyebrow('Checklist'),
                  const SizedBox(height: 6),
                  if (task.checklist.isEmpty)
                    const Text('Nessun elemento checklist.')
                  else
                    for (final item in task.checklist)
                      Row(
                        children: [
                          Checkbox(
                            value: item.isDone,
                            onChanged: (value) async {
                              await _run(() async {
                                await widget.repository.updateChecklistItem(
                                  item.id,
                                  {'is_done': value ?? false},
                                );
                              });
                              if (dialogContext.mounted) {
                                Navigator.of(dialogContext).pop();
                              }
                            },
                          ),
                          Expanded(child: Text(item.title)),
                          IconButton(
                            tooltip: 'Elimina elemento checklist',
                            icon: const Icon(Icons.delete_outline, size: 17),
                            onPressed: () async {
                              final confirmed = await showDialog<bool>(
                                context: dialogContext,
                                builder: (context) => AlertDialog(
                                  backgroundColor: JackPalette.panel,
                                  title: const Text('Eliminare la voce?'),
                                  content: Text(
                                    '“${item.title}” verrà rimossa dalla checklist.',
                                  ),
                                  actions: [
                                    TextButton(
                                      onPressed: () =>
                                          Navigator.pop(context, false),
                                      child: const Text('Annulla'),
                                    ),
                                    FilledButton(
                                      onPressed: () =>
                                          Navigator.pop(context, true),
                                      child: const Text('Elimina'),
                                    ),
                                  ],
                                ),
                              );
                              if (confirmed != true) return;
                              await _run(
                                () => widget.repository.deleteChecklistItem(
                                  item.id,
                                ),
                              );
                              if (dialogContext.mounted) {
                                Navigator.of(dialogContext).pop();
                              }
                            },
                          ),
                        ],
                      ),
                  TextButton.icon(
                    onPressed: () async {
                      final title = await _askText('Nuovo elemento checklist');
                      if (title == null || title.trim().isEmpty) return;
                      await _run(() async {
                        await widget.repository.addChecklistItem(
                          task.id,
                          title.trim(),
                        );
                      });
                      if (dialogContext.mounted) {
                        Navigator.of(dialogContext).pop();
                      }
                    },
                    icon: const Icon(Icons.add, size: 15),
                    label: const Text('Aggiungi voce'),
                  ),
                  const SizedBox(height: 12),
                  const SectionEyebrow('Prerequisiti'),
                  if (task.dependencies.isEmpty)
                    const Text('Nessun prerequisito collegato.')
                  else
                    for (final dependency in task.dependencies)
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(
                          _dependencyTitle(dependency['depends_on_task_id']),
                        ),
                        trailing: IconButton(
                          tooltip: 'Rimuovi prerequisito',
                          icon: const Icon(Icons.link_off, size: 17),
                          onPressed: () async {
                            final dependencyId = dependency['id'];
                            if (dependencyId is! String) return;
                            await _run(
                              () => widget.repository.removeDependency(
                                dependencyId,
                              ),
                            );
                            if (dialogContext.mounted) {
                              Navigator.of(dialogContext).pop();
                            }
                          },
                        ),
                      ),
                  TextButton.icon(
                    onPressed: () =>
                        unawaited(_addDependency(task, dialogContext)),
                    icon: const Icon(Icons.add_link, size: 15),
                    label: const Text('Aggiungi prerequisito'),
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('Chiudi'),
            ),
            TextButton.icon(
              onPressed: () {
                Navigator.pop(dialogContext);
                unawaited(_editTask(task));
              },
              icon: const Icon(Icons.edit_outlined, size: 16),
              label: const Text('Modifica'),
            ),
          ],
        ),
      ),
    );
  }

  Future<String?> _askText(String title) {
    final controller = TextEditingController();
    return showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: JackPalette.panel,
        title: Text(title),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(hintText: 'Scrivi un titolo'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Annulla'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text),
            child: const Text('Aggiungi'),
          ),
        ],
      ),
    ).whenComplete(controller.dispose);
  }

  Future<void> _addDependency(
    PlanningTask task,
    BuildContext dialogContext,
  ) async {
    try {
      final allTasks = await widget.repository.listTasks();
      if (!mounted || !dialogContext.mounted) return;
      final existingIds = task.dependencies
          .map((dependency) => dependency['depends_on_task_id'])
          .toSet();
      final candidates = allTasks
          .where(
            (candidate) =>
                candidate.id != task.id && !existingIds.contains(candidate.id),
          )
          .toList(growable: false);
      if (candidates.isEmpty) {
        _showMessage('Non ci sono altre attività da collegare.');
        return;
      }
      final selectedTaskId = await showDialog<String>(
        context: dialogContext,
        builder: (context) => SimpleDialog(
          backgroundColor: JackPalette.panel,
          title: const Text('Scegli il prerequisito'),
          children: [
            for (final candidate in candidates)
              SimpleDialogOption(
                onPressed: () => Navigator.pop(context, candidate.id),
                child: Text(candidate.title),
              ),
          ],
        ),
      );
      if (selectedTaskId == null) return;
      await _run(
        () => widget.repository.addDependency(task.id, selectedTaskId),
      );
      if (dialogContext.mounted) Navigator.of(dialogContext).pop();
    } on LocalApiException catch (error) {
      if (mounted) _showMessage(error.message, isError: true);
    } on Exception {
      if (mounted) {
        _showMessage(
          'Impossibile caricare le attività disponibili.',
          isError: true,
        );
      }
    }
  }

  String _dependencyTitle(Object? prerequisiteId) {
    for (final task in _tasks) {
      if (task.id == prerequisiteId) return task.title;
    }
    return 'Attività $prerequisiteId';
  }

  Future<void> _showProjectDetails(PlanningProject project) async {
    try {
      final tasks = await widget.repository.listTasks(projectId: project.id);
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          backgroundColor: JackPalette.panel,
          title: Text(project.name),
          content: SizedBox(
            width: 500,
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    project.goal.isNotEmpty
                        ? project.goal
                        : project.description,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    [
                      'Stato ${_projectStatusLabel(project.status)}',
                      _priorityLabel(project.priority),
                      if (project.startDate != null)
                        'Inizio ${project.startDate}',
                      if (project.dueDate != null)
                        'Scadenza ${project.dueDate}',
                    ].join(' · '),
                    style: const TextStyle(
                      color: JackPalette.muted,
                      fontSize: 11,
                    ),
                  ),
                  if (project.notes.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Text(project.notes),
                  ],
                  const SizedBox(height: 14),
                  _ProgressIndicator(percent: project.completionPercent),
                  const SizedBox(height: 16),
                  const SectionEyebrow('Attività aperte'),
                  if (tasks
                      .where(
                        (task) =>
                            task.status != 'completed' &&
                            task.status != 'cancelled',
                      )
                      .isEmpty)
                    const Text('Nessuna attività aperta.')
                  else
                    for (final task in tasks.where(
                      (task) =>
                          task.status != 'completed' &&
                          task.status != 'cancelled',
                    ))
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(task.title),
                        subtitle: Text(_statusLabel(task.status)),
                      ),
                  const SectionEyebrow('Attività completate'),
                  if (tasks.where((task) => task.status == 'completed').isEmpty)
                    const Text('Nessuna attività completata.')
                  else
                    for (final task in tasks.where(
                      (task) => task.status == 'completed',
                    ))
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(task.title),
                        subtitle: const Text('Completata'),
                      ),
                  const SizedBox(height: 10),
                  const SectionEyebrow('Milestone'),
                  if (project.milestones.isEmpty)
                    const Text('Nessuna milestone pianificata.')
                  else
                    for (final milestone in project.milestones)
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: Checkbox(
                          value: milestone.isCompleted,
                          onChanged: (value) async {
                            await _run(
                              () => widget.repository.updateMilestone(
                                milestone.id,
                                {
                                  'completed_at': value == true
                                      ? DateTime.now().toUtc().toIso8601String()
                                      : null,
                                },
                              ),
                            );
                            if (dialogContext.mounted) {
                              Navigator.pop(dialogContext);
                            }
                          },
                        ),
                        title: Text(milestone.title),
                        subtitle: milestone.dueDate == null
                            ? null
                            : Text('Scadenza ${milestone.dueDate}'),
                        trailing: PopupMenuButton<String>(
                          onSelected: (action) {
                            if (action == 'edit') {
                              unawaited(_editMilestone(milestone));
                            } else if (action == 'delete') {
                              unawaited(
                                _confirmDelete(
                                  'Eliminare la milestone?',
                                  'La milestone verrà rimossa dal progetto.',
                                  () => widget.repository.deleteMilestone(
                                    milestone.id,
                                  ),
                                ),
                              );
                            }
                          },
                          itemBuilder: (context) => const [
                            PopupMenuItem(
                              value: 'edit',
                              child: Text('Modifica'),
                            ),
                            PopupMenuItem(
                              value: 'delete',
                              child: Text('Elimina'),
                            ),
                          ],
                        ),
                      ),
                  TextButton.icon(
                    onPressed: () => unawaited(_createMilestone(project.id)),
                    icon: const Icon(Icons.add, size: 15),
                    label: const Text('Aggiungi milestone'),
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('Chiudi'),
            ),
            TextButton(
              onPressed: () {
                Navigator.pop(dialogContext);
                unawaited(_editProject(project));
              },
              child: const Text('Modifica'),
            ),
          ],
        ),
      );
    } on LocalApiException catch (error) {
      if (mounted) _showMessage(error.message, isError: true);
    } on Exception {
      if (mounted) {
        _showMessage('Impossibile caricare il progetto.', isError: true);
      }
    }
  }

  Future<void> _showMissionDetails(PlanningMission mission) async {
    try {
      final allTasks = await widget.repository.listTasks();
      if (!mounted) return;
      final linkedTasks = allTasks
          .where((task) => task.missionId == mission.id)
          .toList(growable: false);
      await showDialog<void>(
        context: context,
        builder: (dialogContext) => StatefulBuilder(
          builder: (context, setDialogState) => AlertDialog(
            backgroundColor: JackPalette.panel,
            title: Text(mission.title),
            content: SizedBox(
              width: 520,
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      mission.description.isEmpty
                          ? 'Nessuna descrizione.'
                          : mission.description,
                    ),
                    if (mission.plan.isNotEmpty) ...[
                      const SizedBox(height: 10),
                      const SectionEyebrow('Piano'),
                      Text(mission.plan),
                    ],
                    const SizedBox(height: 12),
                    _ProgressIndicator(percent: mission.progressPercent),
                    const SizedBox(height: 14),
                    const SectionEyebrow('Attività collegate'),
                    if (linkedTasks.isEmpty)
                      const Text('Nessuna attività collegata.')
                    else
                      for (final task in linkedTasks)
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          title: Text(task.title),
                          subtitle: Text(_statusLabel(task.status)),
                        ),
                    const SectionEyebrow('Agenti assegnati'),
                    Text(
                      mission.assignedAgents.isEmpty
                          ? 'Nessun agente assegnato.'
                          : mission.assignedAgents.join(', '),
                    ),
                    const SizedBox(height: 12),
                    const SectionEyebrow('Log'),
                    if (mission.logs.isEmpty)
                      const Text('Nessuna voce di log.')
                    else
                      for (final log in mission.logs)
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          title: Text(log.message),
                          subtitle: Text(log.createdAt),
                        ),
                    TextButton.icon(
                      onPressed: () async {
                        final message = await _askText('Aggiungi voce al log');
                        if (message == null || message.trim().isEmpty) return;
                        await _run(
                          () => widget.repository.addMissionLog(
                            mission.id,
                            message.trim(),
                          ),
                        );
                        if (dialogContext.mounted) {
                          Navigator.of(dialogContext).pop();
                        }
                      },
                      icon: const Icon(Icons.add, size: 15),
                      label: const Text('Aggiungi log'),
                    ),
                    const SizedBox(height: 8),
                    const SectionEyebrow('Approvazioni'),
                    if (mission.approvals.isEmpty)
                      const Text('Nessuna approvazione richiesta.')
                    else
                      for (final approval in mission.approvals)
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          title: Text(approval.description),
                          subtitle: Text(approval.status),
                          trailing: approval.status == 'pending'
                              ? PopupMenuButton<String>(
                                  onSelected: (status) async {
                                    await _run(
                                      () => widget.repository
                                          .updateMissionApproval(
                                            approval.id,
                                            status,
                                          ),
                                    );
                                    if (dialogContext.mounted) {
                                      Navigator.of(dialogContext).pop();
                                    }
                                  },
                                  itemBuilder: (context) => const [
                                    PopupMenuItem(
                                      value: 'approved',
                                      child: Text('Approva'),
                                    ),
                                    PopupMenuItem(
                                      value: 'rejected',
                                      child: Text('Rifiuta'),
                                    ),
                                  ],
                                )
                              : null,
                        ),
                    TextButton.icon(
                      onPressed: () async {
                        final description = await _askText(
                          'Nuova approvazione',
                        );
                        if (description == null || description.trim().isEmpty) {
                          return;
                        }
                        await _run(
                          () => widget.repository.createMissionApproval(
                            mission.id,
                            description.trim(),
                          ),
                        );
                        if (dialogContext.mounted) {
                          Navigator.of(dialogContext).pop();
                        }
                      },
                      icon: const Icon(Icons.fact_check_outlined, size: 15),
                      label: const Text('Richiedi approvazione'),
                    ),
                  ],
                ),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext),
                child: const Text('Chiudi'),
              ),
              TextButton.icon(
                onPressed: () {
                  Navigator.pop(dialogContext);
                  unawaited(_editMission(mission));
                },
                icon: const Icon(Icons.edit_outlined, size: 16),
                label: const Text('Modifica'),
              ),
            ],
          ),
        ),
      );
    } on LocalApiException catch (error) {
      if (mounted) _showMessage(error.message, isError: true);
    } on Exception {
      if (mounted) {
        _showMessage(
          'Impossibile caricare le attività della missione.',
          isError: true,
        );
      }
    }
  }

  Future<void> _confirmDelete(
    String title,
    String message,
    Future<void> Function() onDelete,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: JackPalette.panel,
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Annulla'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Elimina'),
          ),
        ],
      ),
    );
    if (confirmed == true) await _run(onDelete);
  }

  Future<void> _requestAiPlanning() async {
    final text = await _askText('Chiedi a J.A.C.K. di pianificare');
    if (text == null || text.trim().isEmpty) return;
    try {
      final proposal = await widget.repository.interpret(text.trim());
      if (!mounted) return;
      if (!proposal.understood || proposal.proposalId == null) {
        _showMessage(proposal.message);
        return;
      }
      final approved = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          backgroundColor: JackPalette.panel,
          title: const Text('Riepilogo operazioni'),
          content: SizedBox(
            width: 480,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(proposal.message),
                const SizedBox(height: 12),
                for (final operation in proposal.operations)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text('• ${operation['label'] ?? operation['op']}'),
                  ),
                const Text(
                  'Nessuna modifica viene applicata senza questa conferma.',
                  style: TextStyle(color: JackPalette.muted, fontSize: 12),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Annulla'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Conferma'),
            ),
          ],
        ),
      );
      if (approved != true) return;
      await _run(() async {
        await widget.repository.applyProposal(
          proposalId: proposal.proposalId!,
          confirmed: true,
        );
      });
    } on LocalApiException catch (error) {
      if (mounted) _showMessage(error.message, isError: true);
    } on Exception {
      if (mounted) {
        _showMessage('Impossibile preparare la proposta AI.', isError: true);
      }
    }
  }

  void _onSearch(String value) {
    _query = value;
    _searchTimer?.cancel();
    _searchTimer = Timer(const Duration(milliseconds: 300), _load);
  }

  void _movePeriod(int delta) {
    setState(() {
      switch (_calendarScale) {
        case _CalendarScale.day:
          _selectedDate = _selectedDate.add(Duration(days: delta));
        case _CalendarScale.week:
          _selectedDate = _selectedDate.add(Duration(days: delta * 7));
        case _CalendarScale.month:
          _selectedDate = DateTime(
            _selectedDate.year,
            _selectedDate.month + delta,
            1,
          );
      }
    });
    unawaited(_load());
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _header(),
          const SizedBox(height: 12),
          _filters(),
          const SizedBox(height: 12),
          Expanded(
            child: _loading
                ? const Center(
                    child: CircularProgressIndicator(color: JackPalette.amber),
                  )
                : _error != null
                ? _ErrorState(message: _error!, onRetry: _load)
                : _content(),
          ),
        ],
      ),
    );
  }

  Widget _header() => JackPanel(
    padding: const EdgeInsets.all(16),
    child: LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 720;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SectionEyebrow('Pianificazione'),
                      SizedBox(height: 5),
                      Text(
                        'Dai forma alla giornata.',
                        style: TextStyle(
                          fontSize: 21,
                          fontWeight: FontWeight.w300,
                        ),
                      ),
                    ],
                  ),
                ),
                if (!compact) ...[
                  OutlinedButton.icon(
                    onPressed: _requestAiPlanning,
                    icon: const Icon(Icons.auto_awesome_outlined, size: 16),
                    label: const Text('Chiedi a J.A.C.K.'),
                  ),
                  const SizedBox(width: 8),
                ],
                FilledButton.icon(
                  onPressed: _view == _PlanningView.missions
                      ? _createMission
                      : _createTask,
                  icon: const Icon(Icons.add, size: 17),
                  label: Text(
                    _view == _PlanningView.missions
                        ? 'Nuova missione'
                        : 'Nuova attività',
                  ),
                ),
              ],
            ),
            if (compact) ...[
              const SizedBox(height: 10),
              OutlinedButton.icon(
                onPressed: _requestAiPlanning,
                icon: const Icon(Icons.auto_awesome_outlined, size: 16),
                label: const Text('Chiedi a J.A.C.K.'),
              ),
            ],
            const SizedBox(height: 14),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (final entry in const [
                  (_PlanningView.today, 'Oggi', Icons.today_outlined),
                  (
                    _PlanningView.calendar,
                    'Calendario',
                    Icons.calendar_month_outlined,
                  ),
                  (_PlanningView.tasks, 'Attività', Icons.checklist_rounded),
                  (
                    _PlanningView.projects,
                    'Progetti',
                    Icons.folder_open_outlined,
                  ),
                  (_PlanningView.missions, 'Missioni', Icons.flag_outlined),
                ])
                  _ViewButton(
                    selected: _view == entry.$1,
                    icon: entry.$3,
                    label: entry.$2,
                    onTap: () {
                      setState(() => _view = entry.$1);
                      unawaited(_load());
                    },
                  ),
                const SizedBox(width: 8),
                if (_view == _PlanningView.calendar) ...[
                  _ScaleSelector(
                    value: _calendarScale,
                    onChanged: (scale) {
                      setState(() => _calendarScale = scale);
                      unawaited(_load());
                    },
                  ),
                  IconButton(
                    tooltip: 'Periodo precedente',
                    onPressed: () => _movePeriod(-1),
                    icon: const Icon(Icons.chevron_left),
                  ),
                  IconButton(
                    tooltip: 'Periodo successivo',
                    onPressed: () => _movePeriod(1),
                    icon: const Icon(Icons.chevron_right),
                  ),
                ],
                if (_view == _PlanningView.calendar ||
                    _view == _PlanningView.today)
                  DropdownMenu<String>(
                    initialSelection: _timezone,
                    width: 220,
                    enableFilter: true,
                    requestFocusOnTap: true,
                    label: const Text('Fuso'),
                    dropdownMenuEntries: [
                      for (final timezone in _timezones)
                        DropdownMenuEntry(value: timezone, label: timezone),
                    ],
                    onSelected: (value) {
                      if (value == null) return;
                      unawaited(_changeTimezone(value));
                    },
                  ),
              ],
            ),
          ],
        );
      },
    ),
  );

  Widget _filters() => Wrap(
    spacing: 8,
    runSpacing: 8,
    crossAxisAlignment: WrapCrossAlignment.center,
    children: [
      SizedBox(
        width: 260,
        child: TextField(
          decoration: const InputDecoration(
            hintText: 'Cerca attività e progetti…',
            prefixIcon: Icon(Icons.search, size: 18),
            isDense: true,
          ),
          onChanged: _onSearch,
        ),
      ),
      DropdownButton<String?>(
        value: _statusFilter,
        hint: const Text('Stato'),
        underline: const SizedBox.shrink(),
        items: const [
          DropdownMenuItem(value: null, child: Text('Tutti gli stati')),
          DropdownMenuItem(value: 'inbox', child: Text('Inbox')),
          DropdownMenuItem(value: 'todo', child: Text('Da fare')),
          DropdownMenuItem(value: 'in_progress', child: Text('In corso')),
          DropdownMenuItem(value: 'blocked', child: Text('Bloccate')),
          DropdownMenuItem(value: 'completed', child: Text('Completate')),
          DropdownMenuItem(value: 'cancelled', child: Text('Annullate')),
        ],
        onChanged: (value) {
          setState(() => _statusFilter = value);
          unawaited(_load());
        },
      ),
      DropdownButton<String>(
        value: _sort,
        underline: const SizedBox.shrink(),
        items: const [
          DropdownMenuItem(value: 'due_date', child: Text('Scadenza')),
          DropdownMenuItem(value: 'priority', child: Text('Priorità')),
          DropdownMenuItem(value: 'title', child: Text('Titolo')),
          DropdownMenuItem(value: 'created', child: Text('Creazione')),
        ],
        onChanged: (value) {
          if (value == null) return;
          setState(() => _sort = value);
          unawaited(_load());
        },
      ),
      IconButton(
        tooltip: _sortDescending ? 'Ordine decrescente' : 'Ordine crescente',
        onPressed: () {
          setState(() => _sortDescending = !_sortDescending);
          unawaited(_load());
        },
        icon: Icon(
          _sortDescending ? Icons.south_rounded : Icons.north_rounded,
          size: 17,
        ),
      ),
      DropdownButton<String?>(
        value: _priority,
        hint: const Text('Priorità'),
        underline: const SizedBox.shrink(),
        items: const [
          DropdownMenuItem(value: null, child: Text('Tutte')),
          DropdownMenuItem(value: 'critical', child: Text('Critica')),
          DropdownMenuItem(value: 'high', child: Text('Alta')),
          DropdownMenuItem(value: 'normal', child: Text('Normale')),
          DropdownMenuItem(value: 'low', child: Text('Bassa')),
        ],
        onChanged: (value) {
          setState(() => _priority = value);
          unawaited(_load());
        },
      ),
      DropdownButton<String?>(
        value: _projectId,
        hint: const Text('Progetto'),
        underline: const SizedBox.shrink(),
        items: [
          const DropdownMenuItem(value: null, child: Text('Tutti i progetti')),
          for (final project in _projects)
            DropdownMenuItem(value: project.id, child: Text(project.name)),
        ],
        onChanged: (value) {
          setState(() => _projectId = value);
          unawaited(_load());
        },
      ),
      IconButton(
        tooltip: 'Aggiorna',
        onPressed: _loading ? null : _load,
        icon: const Icon(Icons.refresh),
      ),
    ],
  );

  Widget _content() {
    return switch (_view) {
      _PlanningView.today => _todayContent(),
      _PlanningView.calendar => _calendarContent(),
      _PlanningView.tasks => _taskContent(_tasks),
      _PlanningView.projects => _projectContent(),
      _PlanningView.missions => _missionContent(),
    };
  }

  Widget _todayContent() {
    final overdue = _tasks.where(_isOverdue).toList(growable: false);
    final tasks = _tasks.where(
      (task) => task.dueDate == _dateOnly(_selectedDate),
    );
    final events = _visibleEvents;
    return ListView(
      children: [
        _summaryCard(overdue.length, tasks.length, events.length),
        if (overdue.isNotEmpty) ...[
          const SizedBox(height: 12),
          _SectionTitle(title: 'In ritardo', trailing: '${overdue.length}'),
          ...overdue.map(_taskTile),
        ],
        const SizedBox(height: 12),
        _SectionTitle(
          title: 'Attività · ${_formatDate(_selectedDate)}',
          trailing: '${tasks.length}',
        ),
        if (tasks.isEmpty)
          const _EmptyState(
            icon: Icons.check_circle_outline,
            title: 'La giornata è libera',
            subtitle: 'Le attività con scadenza oggi appariranno qui.',
          )
        else
          ...tasks.map(_taskTile),
        const SizedBox(height: 12),
        _SectionTitle(title: 'Appuntamenti', trailing: '${events.length}'),
        if (events.isEmpty)
          const _EmptyState(
            icon: Icons.event_available_outlined,
            title: 'Nessun appuntamento',
            subtitle:
                'Le scadenze delle attività restano distinte dagli eventi.',
          )
        else
          ...events.map(_eventTile),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            onPressed: _createEvent,
            icon: const Icon(Icons.add, size: 16),
            label: const Text('Aggiungi appuntamento'),
          ),
        ),
      ],
    );
  }

  Widget _summaryCard(int overdueCount, int todayCount, int eventCount) =>
      JackPanel(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            _Metric(value: '$todayCount', label: 'ATTIVITÀ OGGI'),
            const SizedBox(width: 30),
            _Metric(
              value: '$overdueCount',
              label: 'IN RITARDO',
              color: overdueCount == 0 ? JackPalette.green : JackPalette.red,
            ),
            const SizedBox(width: 30),
            _Metric(value: '$eventCount', label: 'APPUNTAMENTI'),
          ],
        ),
      );

  Widget _calendarContent() {
    final range = _visibleRange;
    final tasks = _calendar?.tasks ?? const <PlanningTask>[];
    final events = _visibleEvents;
    if (_calendarScale != _CalendarScale.day) {
      final days = <DateTime>[];
      for (
        var date = range.$1;
        !date.isAfter(range.$2);
        date = date.add(const Duration(days: 1))
      ) {
        days.add(date);
      }
      return Column(
        children: [
          if (_calendarScale == _CalendarScale.month)
            _monthGrid(days, tasks, events)
          else
            _weekGrid(days, tasks, events),
          const SizedBox(height: 10),
          Expanded(child: _calendarItems(tasks, events)),
        ],
      );
    }
    return _calendarItems(tasks, events);
  }

  Widget _monthGrid(
    List<DateTime> days,
    List<PlanningTask> tasks,
    List<PlanningEvent> events,
  ) {
    final leading = days.first.weekday - 1;
    final cells = <Widget>[
      for (var i = 0; i < leading; i++) const SizedBox.shrink(),
      for (final day in days)
        _CalendarDayCell(
          date: day,
          selected: DateUtils.isSameDay(day, _selectedDate),
          count: _countForDay(day, tasks, events),
          onTap: () {
            setState(() {
              _selectedDate = day;
              _calendarScale = _CalendarScale.day;
            });
            unawaited(_load());
          },
        ),
    ];
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Row(
            children: [
              for (final day in const ['L', 'M', 'M', 'G', 'V', 'S', 'D'])
                Expanded(
                  child: Center(
                    child: Text(
                      day,
                      style: const TextStyle(
                        color: JackPalette.dim,
                        fontSize: 10,
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
        GridView.count(
          crossAxisCount: 7,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          childAspectRatio: 2.3,
          children: cells,
        ),
      ],
    );
  }

  Widget _weekGrid(
    List<DateTime> days,
    List<PlanningTask> tasks,
    List<PlanningEvent> events,
  ) => SizedBox(
    height: 75,
    child: Row(
      children: [
        for (final day in days)
          Expanded(
            child: _CalendarDayCell(
              date: day,
              selected: DateUtils.isSameDay(day, _selectedDate),
              count: _countForDay(day, tasks, events),
              onTap: () {
                setState(() {
                  _selectedDate = day;
                  _calendarScale = _CalendarScale.day;
                });
                unawaited(_load());
              },
            ),
          ),
      ],
    ),
  );

  int _countForDay(
    DateTime day,
    List<PlanningTask> tasks,
    List<PlanningEvent> events,
  ) {
    final date = _dateOnly(day);
    return tasks.where((task) => task.dueDate == date).length +
        events.where((event) {
          final start = DateTime.tryParse(
            event.occurrenceStartsAt ?? event.startsAt,
          );
          return start != null && DateUtils.isSameDay(start.toLocal(), day);
        }).length;
  }

  Widget _calendarItems(List<PlanningTask> tasks, List<PlanningEvent> events) {
    final day = _dateOnly(_selectedDate);
    final dayTasks = tasks.where((task) => task.dueDate == day).toList();
    final dayEvents = events.where((event) {
      final start = DateTime.tryParse(
        event.occurrenceStartsAt ?? event.startsAt,
      );
      return start != null &&
          DateUtils.isSameDay(start.toLocal(), _selectedDate);
    }).toList();
    return ListView(
      children: [
        _SectionTitle(
          title: _view == _PlanningView.calendar
              ? _rangeLabel(_visibleRange)
              : _formatDate(_selectedDate),
          trailing: '${dayTasks.length + dayEvents.length}',
        ),
        if (_calendarScale == _CalendarScale.day &&
            dayTasks.isEmpty &&
            dayEvents.isEmpty)
          const _EmptyState(
            icon: Icons.calendar_today_outlined,
            title: 'Nessun elemento in questo giorno',
            subtitle: 'Aggiungi un’attività con scadenza o un appuntamento.',
          ),
        ...dayTasks.map(_taskTile),
        ...dayEvents.map(_eventTile),
        TextButton.icon(
          onPressed: _createEvent,
          icon: const Icon(Icons.add, size: 16),
          label: const Text('Nuovo appuntamento'),
        ),
      ],
    );
  }

  Widget _taskContent(List<PlanningTask> tasks) => Column(
    children: [
      Align(
        alignment: Alignment.centerLeft,
        child: TextButton.icon(
          onPressed: () => _createTask(),
          icon: const Icon(Icons.add, size: 16),
          label: const Text('Crea attività'),
        ),
      ),
      Expanded(
        child: tasks.isEmpty
            ? const _EmptyState(
                icon: Icons.task_alt_outlined,
                title: 'Nessuna attività trovata',
                subtitle:
                    'Crea la prima attività o modifica i filtri di ricerca.',
              )
            : ListView(children: tasks.map(_taskTile).toList()),
      ),
    ],
  );

  Widget _projectContent() => Column(
    children: [
      Align(
        alignment: Alignment.centerLeft,
        child: TextButton.icon(
          onPressed: _createProject,
          icon: const Icon(Icons.create_new_folder_outlined, size: 16),
          label: const Text('Crea progetto'),
        ),
      ),
      Expanded(
        child: _projects.isEmpty
            ? const _EmptyState(
                icon: Icons.folder_open_outlined,
                title: 'Nessun progetto',
                subtitle: 'Crea un progetto per raggruppare le attività.',
              )
            : ListView(
                children: _projects.map(_projectTile).toList(growable: false),
              ),
      ),
    ],
  );

  Widget _missionContent() => Column(
    children: [
      Align(
        alignment: Alignment.centerLeft,
        child: TextButton.icon(
          onPressed: _createMission,
          icon: const Icon(Icons.flag_outlined, size: 16),
          label: const Text('Pianifica missione'),
        ),
      ),
      Expanded(
        child: _missions.isEmpty
            ? const _EmptyState(
                icon: Icons.flag_outlined,
                title: 'Nessuna missione pianificata',
                subtitle: 'Definisci un obiettivo e collegalo alle attività da svolgere.',
              )
            : ListView(
                children: _missions.map(_missionTile).toList(growable: false),
              ),
      ),
    ],
  );

  Widget _missionTile(PlanningMission mission) => Padding(
    padding: const EdgeInsets.only(bottom: 7),
    child: InkWell(
      onTap: () => _showMissionDetails(mission),
      borderRadius: BorderRadius.circular(14),
      child: JackPanel(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        child: Row(
          children: [
            const Icon(Icons.flag_outlined, color: JackPalette.cyan, size: 19),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    mission.title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    [
                      _missionStatusLabel(mission.status),
                      '${mission.taskIds.length} attività',
                      if (mission.logs.isNotEmpty)
                        '${mission.logs.length} aggiornamenti',
                    ].join(' · '),
                    style: const TextStyle(
                      color: JackPalette.muted,
                      fontSize: 10,
                    ),
                  ),
                ],
              ),
            ),
            PopupMenuButton<String>(
              onSelected: (action) {
                if (action == 'edit') {
                  unawaited(_editMission(mission));
                } else if (action == 'delete') {
                  unawaited(
                    _confirmDelete(
                      'Eliminare la missione?',
                      'La missione verrà eliminata; le attività collegate resteranno disponibili.',
                      () => widget.repository.deleteMission(mission.id),
                    ),
                  );
                }
              },
              itemBuilder: (context) => const [
                PopupMenuItem(value: 'edit', child: Text('Modifica')),
                PopupMenuItem(value: 'delete', child: Text('Elimina')),
              ],
            ),
          ],
        ),
      ),
    ),
  );

  Widget _taskTile(PlanningTask task) => Padding(
    padding: const EdgeInsets.only(bottom: 7),
    child: InkWell(
      onTap: () => _showTaskDetails(task),
      borderRadius: BorderRadius.circular(14),
      child: JackPanel(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        child: Row(
          children: [
            IconButton(
              tooltip: task.status == 'completed'
                  ? 'Attività completata'
                  : 'Completa attività',
              onPressed: task.status == 'completed' || _saving
                  ? null
                  : () => _run(() async {
                      await widget.repository.completeTask(task.id);
                    }),
              icon: Icon(
                task.status == 'completed'
                    ? Icons.check_circle
                    : Icons.radio_button_unchecked,
                color: task.status == 'completed'
                    ? JackPalette.green
                    : JackPalette.muted,
                size: 19,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    task.title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      decoration: task.status == 'completed'
                          ? TextDecoration.lineThrough
                          : null,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    [
                      if (task.dueDate != null) task.dueDate!,
                      _statusLabel(task.status),
                      _priorityLabel(task.priority),
                    ].join(' · '),
                    style: const TextStyle(
                      color: JackPalette.muted,
                      fontSize: 10,
                    ),
                  ),
                ],
              ),
            ),
            _PriorityDot(priority: task.priority),
            PopupMenuButton<String>(
              onSelected: (action) {
                switch (action) {
                  case 'edit':
                    unawaited(_editTask(task));
                  case 'delete':
                    unawaited(
                      _confirmDelete(
                        'Eliminare attività?',
                        '“${task.title}” e i suoi elementi checklist verranno eliminati.',
                        () => widget.repository.deleteTask(task.id),
                      ),
                    );
                }
              },
              itemBuilder: (context) => const [
                PopupMenuItem(value: 'edit', child: Text('Modifica')),
                PopupMenuItem(value: 'delete', child: Text('Elimina')),
              ],
            ),
          ],
        ),
      ),
    ),
  );

  Widget _eventTile(PlanningEvent event) {
    final starts = DateTime.tryParse(
      event.occurrenceStartsAt ?? event.startsAt,
    );
    final ends = DateTime.tryParse(event.occurrenceEndsAt ?? event.endsAt);
    return Padding(
      padding: const EdgeInsets.only(bottom: 7),
      child: InkWell(
        onTap: () => _editEvent(event),
        borderRadius: BorderRadius.circular(14),
        child: JackPanel(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          child: Row(
            children: [
              const Icon(
                Icons.event_outlined,
                color: JackPalette.cyan,
                size: 19,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  event.title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Text(
                '${starts == null ? '' : _time(starts.toLocal())}'
                '${ends == null ? '' : ' – ${_time(ends.toLocal())}'}',
                style: const TextStyle(color: JackPalette.muted, fontSize: 11),
              ),
              PopupMenuButton<String>(
                onSelected: (action) {
                  if (action == 'edit') unawaited(_editEvent(event));
                  if (action == 'delete') {
                    unawaited(
                      _confirmDelete(
                        'Eliminare appuntamento?',
                        '“${event.title}” verrà rimosso dal calendario.',
                        () => widget.repository.deleteEvent(event.id),
                      ),
                    );
                  }
                },
                itemBuilder: (context) => const [
                  PopupMenuItem(value: 'edit', child: Text('Modifica serie')),
                  PopupMenuItem(value: 'delete', child: Text('Elimina serie')),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _projectTile(PlanningProject project) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: InkWell(
      onTap: () => _showProjectDetails(project),
      borderRadius: BorderRadius.circular(14),
      child: JackPanel(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.folder_outlined,
                  color: JackPalette.amber,
                  size: 18,
                ),
                const SizedBox(width: 9),
                Expanded(
                  child: Text(
                    project.name,
                    style: const TextStyle(fontWeight: FontWeight.w500),
                  ),
                ),
                Text(
                  '${project.completionPercent}%',
                  style: const TextStyle(color: JackPalette.cyan, fontSize: 12),
                ),
                PopupMenuButton<String>(
                  onSelected: (action) {
                    switch (action) {
                      case 'edit':
                        unawaited(_editProject(project));
                      case 'archive':
                        unawaited(
                          _run(() async {
                            await widget.repository.archiveProject(project.id);
                          }),
                        );
                      case 'delete':
                        unawaited(
                          _confirmDelete(
                            'Eliminare il progetto?',
                            'Le attività resteranno salvate ma non saranno più associate al progetto.',
                            () => widget.repository.deleteProject(project.id),
                          ),
                        );
                    }
                  },
                  itemBuilder: (context) => const [
                    PopupMenuItem(value: 'edit', child: Text('Modifica')),
                    PopupMenuItem(value: 'archive', child: Text('Archivia')),
                    PopupMenuItem(value: 'delete', child: Text('Elimina')),
                  ],
                ),
              ],
            ),
            if (project.description.isNotEmpty) ...[
              const SizedBox(height: 5),
              Text(
                project.description,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: JackPalette.muted, fontSize: 11),
              ),
            ],
            const SizedBox(height: 10),
            _ProgressIndicator(percent: project.completionPercent),
            const SizedBox(height: 7),
            Text(
              '${project.openTaskCount} aperte · ${project.completedTaskCount} completate'
              '${project.dueDate == null ? '' : ' · scadenza ${project.dueDate}'}',
              style: const TextStyle(color: JackPalette.dim, fontSize: 10),
            ),
          ],
        ),
      ),
    ),
  );

  bool _isOverdue(PlanningTask task) =>
      task.dueDate != null &&
      task.dueDate!.compareTo(_dateOnly(DateTime.now())) < 0 &&
      task.status != 'completed' &&
      task.status != 'cancelled';

  String _missionTitle(String missionId) {
    for (final mission in _missions) {
      if (mission.id == missionId) return mission.title;
    }
    return 'non disponibile';
  }
}

class _TaskEditorDialog extends StatefulWidget {
  const _TaskEditorDialog({
    required this.projects,
    required this.missions,
    this.task,
    this.initialTitle,
  });

  final List<PlanningProject> projects;
  final List<PlanningMission> missions;
  final PlanningTask? task;
  final String? initialTitle;

  @override
  State<_TaskEditorDialog> createState() => _TaskEditorDialogState();
}

class _TaskEditorDialogState extends State<_TaskEditorDialog> {
  late final TextEditingController _title;
  late final TextEditingController _description;
  late final TextEditingController _category;
  late final TextEditingController _notes;
  late final TextEditingController _tags;
  late final TextEditingController _responsibleAgent;
  String _status = 'todo';
  String _priority = 'normal';
  String _recurrence = 'none';
  String? _projectId;
  String? _missionId;
  DateTime? _startDate;
  DateTime? _dueDate;
  int _recurrenceInterval = 1;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    final task = widget.task;
    _title = TextEditingController(
      text: task?.title ?? widget.initialTitle ?? '',
    );
    _description = TextEditingController(text: task?.description ?? '');
    _category = TextEditingController(text: task?.category ?? '');
    _notes = TextEditingController(text: task?.notes ?? '');
    _tags = TextEditingController(text: task?.tags.join(', ') ?? '');
    _responsibleAgent = TextEditingController(
      text: task?.responsibleAgent ?? '',
    );
    _status = task?.status ?? 'todo';
    _priority = task?.priority ?? 'normal';
    _recurrence = task?.recurrenceKind ?? 'none';
    _projectId = task?.projectId;
    _missionId = task?.missionId;
    _startDate = task?.startDate == null
        ? null
        : DateTime.tryParse(task!.startDate!);
    _dueDate = task?.dueDate == null ? null : DateTime.tryParse(task!.dueDate!);
    _recurrenceInterval = task?.recurrenceInterval ?? 1;
  }

  @override
  void dispose() {
    _title.dispose();
    _description.dispose();
    _category.dispose();
    _notes.dispose();
    _tags.dispose();
    _responsibleAgent.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    backgroundColor: JackPalette.panel,
    title: Text(widget.task == null ? 'Nuova attività' : 'Modifica attività'),
    content: SizedBox(
      width: 520,
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _title,
              autofocus: true,
              maxLength: 200,
              decoration: const InputDecoration(labelText: 'Titolo *'),
            ),
            TextField(
              controller: _description,
              maxLines: 3,
              decoration: const InputDecoration(labelText: 'Descrizione'),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String>(
                    initialValue: _status,
                    decoration: const InputDecoration(labelText: 'Stato'),
                    items: const [
                      DropdownMenuItem(value: 'inbox', child: Text('Inbox')),
                      DropdownMenuItem(value: 'todo', child: Text('Da fare')),
                      DropdownMenuItem(
                        value: 'in_progress',
                        child: Text('In corso'),
                      ),
                      DropdownMenuItem(
                        value: 'blocked',
                        child: Text('Bloccata'),
                      ),
                      DropdownMenuItem(
                        value: 'cancelled',
                        child: Text('Annullata'),
                      ),
                    ],
                    onChanged: (value) =>
                        setState(() => _status = value ?? 'todo'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: DropdownButtonFormField<String>(
                    initialValue: _priority,
                    decoration: const InputDecoration(labelText: 'Priorità'),
                    items: const [
                      DropdownMenuItem(value: 'low', child: Text('Bassa')),
                      DropdownMenuItem(value: 'normal', child: Text('Normale')),
                      DropdownMenuItem(value: 'high', child: Text('Alta')),
                      DropdownMenuItem(
                        value: 'critical',
                        child: Text('Critica'),
                      ),
                    ],
                    onChanged: (value) =>
                        setState(() => _priority = value ?? 'normal'),
                  ),
                ),
              ],
            ),
            DropdownButtonFormField<String?>(
              initialValue: _projectId,
              decoration: const InputDecoration(labelText: 'Progetto'),
              items: [
                const DropdownMenuItem(
                  value: null,
                  child: Text('Nessun progetto'),
                ),
                for (final project in widget.projects)
                  DropdownMenuItem(
                    value: project.id,
                    child: Text(project.name),
                  ),
              ],
              onChanged: (value) => setState(() => _projectId = value),
            ),
            DropdownButtonFormField<String?>(
              initialValue: _missionId,
              decoration: const InputDecoration(labelText: 'Missione'),
              items: [
                const DropdownMenuItem(
                  value: null,
                  child: Text('Nessuna missione'),
                ),
                for (final mission in widget.missions)
                  DropdownMenuItem(
                    value: mission.id,
                    child: Text(mission.title),
                  ),
              ],
              onChanged: (value) => setState(() => _missionId = value),
            ),
            TextField(
              controller: _category,
              decoration: const InputDecoration(labelText: 'Categoria'),
            ),
            TextField(
              controller: _tags,
              decoration: const InputDecoration(
                labelText: 'Tag',
                helperText: 'Separati da virgola',
              ),
            ),
            TextField(
              controller: _responsibleAgent,
              decoration: const InputDecoration(
                labelText: 'Agente responsabile',
              ),
            ),
            TextField(
              controller: _notes,
              maxLines: 2,
              decoration: const InputDecoration(labelText: 'Note'),
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () async {
                      final value = await showDatePicker(
                        context: context,
                        initialDate: _startDate ?? DateTime.now(),
                        firstDate: DateTime(2000),
                        lastDate: DateTime(2200),
                      );
                      if (value != null) setState(() => _startDate = value);
                    },
                    icon: const Icon(Icons.play_arrow, size: 16),
                    label: Text(
                      _startDate == null
                          ? 'Imposta inizio'
                          : 'Inizia ${_dateOnly(_startDate!)}',
                    ),
                  ),
                ),
                if (_startDate != null)
                  IconButton(
                    tooltip: 'Rimuovi data di inizio',
                    onPressed: () => setState(() => _startDate = null),
                    icon: const Icon(Icons.close, size: 16),
                  ),
                const SizedBox(width: 6),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () async {
                      final value = await showDatePicker(
                        context: context,
                        initialDate: _dueDate ?? DateTime.now(),
                        firstDate: DateTime(2000),
                        lastDate: DateTime(2200),
                      );
                      if (value != null) setState(() => _dueDate = value);
                    },
                    icon: const Icon(Icons.event, size: 16),
                    label: Text(
                      _dueDate == null
                          ? 'Imposta scadenza'
                          : 'Scade ${_dateOnly(_dueDate!)}',
                    ),
                  ),
                ),
                if (_dueDate != null)
                  IconButton(
                    tooltip: 'Rimuovi scadenza',
                    onPressed: () => setState(() => _dueDate = null),
                    icon: const Icon(Icons.close, size: 16),
                  ),
              ],
            ),
            DropdownButtonFormField<String>(
              initialValue: _recurrence,
              decoration: const InputDecoration(labelText: 'Ricorrenza'),
              items: const [
                DropdownMenuItem(value: 'none', child: Text('Nessuna')),
                DropdownMenuItem(value: 'daily', child: Text('Ogni giorno')),
                DropdownMenuItem(
                  value: 'weekly',
                  child: Text('Ogni settimana'),
                ),
                DropdownMenuItem(value: 'monthly', child: Text('Ogni mese')),
              ],
              onChanged: (value) =>
                  setState(() => _recurrence = value ?? 'none'),
            ),
            if (_recurrence != 'none') ...[
              TextFormField(
                initialValue: '$_recurrenceInterval',
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Intervallo ricorrenza',
                  helperText: 'Per esempio 2 = ogni due settimane',
                ),
                onChanged: (value) {
                  final parsed = int.tryParse(value);
                  if (parsed != null && parsed > 0) {
                    _recurrenceInterval = parsed;
                  }
                },
              ),
            ],
          ],
        ),
      ),
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Annulla'),
      ),
      FilledButton(
        onPressed: _busy
            ? null
            : () {
                if (_title.text.trim().isEmpty) return;
                setState(() => _busy = true);
                final draft = <String, Object?>{
                  'title': _title.text.trim(),
                  'description': _description.text.trim(),
                  'status': _status,
                  'priority': _priority,
                  'category': _category.text.trim(),
                  'tags': _tags.text
                      .split(',')
                      .map((tag) => tag.trim())
                      .where((tag) => tag.isNotEmpty)
                      .toList(growable: false),
                  'notes': _notes.text.trim(),
                  'responsible_agent': _responsibleAgent.text.trim().isEmpty
                      ? null
                      : _responsibleAgent.text.trim(),
                  'project_id': _projectId,
                  'mission_id': _missionId,
                  'start_date': _startDate == null
                      ? null
                      : _dateOnly(_startDate!),
                  'due_date': _dueDate == null ? null : _dateOnly(_dueDate!),
                  'recurrence_kind': _recurrence,
                  'recurrence_interval': _recurrenceInterval,
                };
                Navigator.pop(context, draft);
              },
        child: const Text('Salva'),
      ),
    ],
  );
}

class _ProjectEditorDialog extends StatefulWidget {
  const _ProjectEditorDialog({this.project});

  final PlanningProject? project;

  @override
  State<_ProjectEditorDialog> createState() => _ProjectEditorDialogState();
}

class _ProjectEditorDialogState extends State<_ProjectEditorDialog> {
  late final TextEditingController _name;
  late final TextEditingController _description;
  late final TextEditingController _goal;
  late final TextEditingController _notes;
  String _status = 'active';
  String _priority = 'normal';
  DateTime? _startDate;
  DateTime? _dueDate;

  @override
  void initState() {
    super.initState();
    _name = TextEditingController(text: widget.project?.name ?? '');
    _description = TextEditingController(
      text: widget.project?.description ?? '',
    );
    _goal = TextEditingController(text: widget.project?.goal ?? '');
    _notes = TextEditingController(text: widget.project?.notes ?? '');
    _status = widget.project?.status ?? 'active';
    _priority = widget.project?.priority ?? 'normal';
    _startDate = widget.project?.startDate == null
        ? null
        : DateTime.tryParse(widget.project!.startDate!);
    _dueDate = widget.project?.dueDate == null
        ? null
        : DateTime.tryParse(widget.project!.dueDate!);
  }

  @override
  void dispose() {
    _name.dispose();
    _description.dispose();
    _goal.dispose();
    _notes.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    backgroundColor: JackPalette.panel,
    title: Text(
      widget.project == null ? 'Nuovo progetto' : 'Modifica progetto',
    ),
    content: SizedBox(
      width: 480,
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _name,
              autofocus: true,
              decoration: const InputDecoration(labelText: 'Nome *'),
            ),
            TextField(
              controller: _goal,
              maxLines: 2,
              decoration: const InputDecoration(labelText: 'Obiettivo'),
            ),
            TextField(
              controller: _description,
              maxLines: 3,
              decoration: const InputDecoration(labelText: 'Descrizione'),
            ),
            DropdownButtonFormField<String>(
              initialValue: _status,
              decoration: const InputDecoration(labelText: 'Stato'),
              items: const [
                DropdownMenuItem(value: 'active', child: Text('Attivo')),
                DropdownMenuItem(value: 'on_hold', child: Text('In pausa')),
                DropdownMenuItem(value: 'completed', child: Text('Completato')),
                DropdownMenuItem(value: 'archived', child: Text('Archiviato')),
              ],
              onChanged: (value) => setState(() => _status = value ?? 'active'),
            ),
            DropdownButtonFormField<String>(
              initialValue: _priority,
              decoration: const InputDecoration(labelText: 'Priorità'),
              items: const [
                DropdownMenuItem(value: 'low', child: Text('Bassa')),
                DropdownMenuItem(value: 'normal', child: Text('Normale')),
                DropdownMenuItem(value: 'high', child: Text('Alta')),
                DropdownMenuItem(value: 'critical', child: Text('Critica')),
              ],
              onChanged: (value) =>
                  setState(() => _priority = value ?? 'normal'),
            ),
            TextField(
              controller: _notes,
              maxLines: 2,
              decoration: const InputDecoration(labelText: 'Note'),
            ),
            TextButton.icon(
              onPressed: () async {
                final value = await showDatePicker(
                  context: context,
                  initialDate: _startDate ?? DateTime.now(),
                  firstDate: DateTime(2000),
                  lastDate: DateTime(2200),
                );
                if (value != null) setState(() => _startDate = value);
              },
              icon: const Icon(Icons.play_arrow, size: 16),
              label: Text(
                _startDate == null
                    ? 'Imposta data di inizio'
                    : 'Inizia ${_dateOnly(_startDate!)}',
              ),
            ),
            TextButton.icon(
              onPressed: () async {
                final value = await showDatePicker(
                  context: context,
                  initialDate: _dueDate ?? DateTime.now(),
                  firstDate: DateTime(2000),
                  lastDate: DateTime(2200),
                );
                if (value != null) setState(() => _dueDate = value);
              },
              icon: const Icon(Icons.event, size: 16),
              label: Text(
                _dueDate == null
                    ? 'Imposta scadenza'
                    : 'Scade ${_dateOnly(_dueDate!)}',
              ),
            ),
          ],
        ),
      ),
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Annulla'),
      ),
      FilledButton(
        onPressed: () {
          if (_name.text.trim().isEmpty) return;
          Navigator.pop(context, <String, Object?>{
            'name': _name.text.trim(),
            'goal': _goal.text.trim(),
            'description': _description.text.trim(),
            'priority': _priority,
            'status': _status,
            'notes': _notes.text.trim(),
            'start_date': _startDate == null ? null : _dateOnly(_startDate!),
            'due_date': _dueDate == null ? null : _dateOnly(_dueDate!),
          });
        },
        child: const Text('Salva'),
      ),
    ],
  );
}

class _MilestoneEditorDialog extends StatefulWidget {
  const _MilestoneEditorDialog({this.milestone});

  final ProjectMilestone? milestone;

  @override
  State<_MilestoneEditorDialog> createState() => _MilestoneEditorDialogState();
}

class _MilestoneEditorDialogState extends State<_MilestoneEditorDialog> {
  late final TextEditingController _title;
  late final TextEditingController _description;
  DateTime? _dueDate;

  @override
  void initState() {
    super.initState();
    _title = TextEditingController(text: widget.milestone?.title ?? '');
    _description = TextEditingController(
      text: widget.milestone?.description ?? '',
    );
    _dueDate = widget.milestone?.dueDate == null
        ? null
        : DateTime.tryParse(widget.milestone!.dueDate!);
  }

  @override
  void dispose() {
    _title.dispose();
    _description.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    backgroundColor: JackPalette.panel,
    title: Text(
      widget.milestone == null ? 'Nuova milestone' : 'Modifica milestone',
    ),
    content: SizedBox(
      width: 420,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            controller: _title,
            autofocus: true,
            maxLength: 200,
            decoration: const InputDecoration(labelText: 'Titolo *'),
          ),
          TextField(
            controller: _description,
            maxLines: 3,
            decoration: const InputDecoration(labelText: 'Descrizione'),
          ),
          TextButton.icon(
            onPressed: () async {
              final value = await showDatePicker(
                context: context,
                initialDate: _dueDate ?? DateTime.now(),
                firstDate: DateTime(2000),
                lastDate: DateTime(2200),
              );
              if (value != null) setState(() => _dueDate = value);
            },
            icon: const Icon(Icons.event, size: 16),
            label: Text(
              _dueDate == null
                  ? 'Imposta scadenza'
                  : 'Scade ${_dateOnly(_dueDate!)}',
            ),
          ),
        ],
      ),
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Annulla'),
      ),
      FilledButton(
        onPressed: () {
          if (_title.text.trim().isEmpty) return;
          Navigator.pop(context, <String, Object?>{
            'title': _title.text.trim(),
            'description': _description.text.trim(),
            'due_date': _dueDate == null ? null : _dateOnly(_dueDate!),
          });
        },
        child: const Text('Salva'),
      ),
    ],
  );
}

class _MissionEditorDialog extends StatefulWidget {
  const _MissionEditorDialog({this.mission});

  final PlanningMission? mission;

  @override
  State<_MissionEditorDialog> createState() => _MissionEditorDialogState();
}

class _MissionEditorDialogState extends State<_MissionEditorDialog> {
  late final TextEditingController _title;
  late final TextEditingController _description;
  late final TextEditingController _plan;
  late final TextEditingController _agents;
  late final TextEditingController _results;
  late final TextEditingController _notes;
  String _status = 'planned';

  @override
  void initState() {
    super.initState();
    final mission = widget.mission;
    _title = TextEditingController(text: mission?.title ?? '');
    _description = TextEditingController(text: mission?.description ?? '');
    _plan = TextEditingController(text: mission?.plan ?? '');
    _agents = TextEditingController(
      text: mission?.assignedAgents.join(', ') ?? '',
    );
    _results = TextEditingController(text: mission?.results ?? '');
    _notes = TextEditingController(text: mission?.notes ?? '');
    _status = mission?.status ?? 'planned';
  }

  @override
  void dispose() {
    _title.dispose();
    _description.dispose();
    _plan.dispose();
    _agents.dispose();
    _results.dispose();
    _notes.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    backgroundColor: JackPalette.panel,
    title: Text(
      widget.mission == null ? 'Pianifica missione' : 'Modifica missione',
    ),
    content: SizedBox(
      width: 500,
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _title,
              autofocus: true,
              maxLength: 200,
              decoration: const InputDecoration(labelText: 'Obiettivo *'),
            ),
            TextField(
              controller: _description,
              maxLines: 3,
              decoration: const InputDecoration(labelText: 'Descrizione'),
            ),
            TextField(
              controller: _plan,
              maxLines: 4,
              decoration: const InputDecoration(labelText: 'Piano'),
            ),
            DropdownButtonFormField<String>(
              initialValue: _status,
              decoration: const InputDecoration(labelText: 'Stato'),
              items: const [
                DropdownMenuItem(value: 'planned', child: Text('Pianificata')),
                DropdownMenuItem(
                  value: 'pending_approval',
                  child: Text('In attesa di approvazione'),
                ),
                DropdownMenuItem(value: 'approved', child: Text('Approvata')),
                DropdownMenuItem(value: 'cancelled', child: Text('Annullata')),
              ],
              onChanged: (value) =>
                  setState(() => _status = value ?? 'planned'),
            ),
            TextField(
              controller: _agents,
              decoration: const InputDecoration(
                labelText: 'Agenti assegnati',
                helperText:
                    'Separati da virgola; l’esecuzione autonoma non è attiva.',
              ),
            ),
            TextField(
              controller: _results,
              maxLines: 2,
              decoration: const InputDecoration(labelText: 'Risultati'),
            ),
            TextField(
              controller: _notes,
              maxLines: 2,
              decoration: const InputDecoration(labelText: 'Note'),
            ),
          ],
        ),
      ),
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Annulla'),
      ),
      FilledButton(
        onPressed: () {
          if (_title.text.trim().isEmpty) return;
          Navigator.pop(context, <String, Object?>{
            'title': _title.text.trim(),
            'description': _description.text.trim(),
            'plan': _plan.text.trim(),
            'status': _status,
            'assigned_agents': _agents.text
                .split(',')
                .map((agent) => agent.trim())
                .where((agent) => agent.isNotEmpty)
                .toList(growable: false),
            'results': _results.text.trim(),
            'notes': _notes.text.trim(),
          });
        },
        child: const Text('Salva'),
      ),
    ],
  );
}

class _EventEditorDialog extends StatefulWidget {
  const _EventEditorDialog({
    required this.projects,
    required this.timezones,
    required this.initialTimezone,
    this.event,
  });

  final List<PlanningProject> projects;
  final List<String> timezones;
  final String initialTimezone;
  final PlanningEvent? event;

  @override
  State<_EventEditorDialog> createState() => _EventEditorDialogState();
}

class _EventEditorDialogState extends State<_EventEditorDialog> {
  late final TextEditingController _title;
  late final TextEditingController _description;
  late DateTime _startsAt;
  late DateTime _endsAt;
  String _timezone = 'Europe/Rome';
  String _recurrence = 'none';
  String _priority = 'normal';
  String? _projectId;
  int _recurrenceInterval = 1;
  DateTime? _recurrenceUntil;

  @override
  void initState() {
    super.initState();
    final event = widget.event;
    _title = TextEditingController(text: event?.title ?? '');
    _description = TextEditingController(text: event?.description ?? '');
    _startsAt = event == null
        ? DateTime.now().add(const Duration(hours: 1))
        : DateTime.parse(event.startsAt).toLocal();
    _endsAt = event == null
        ? _startsAt.add(const Duration(hours: 1))
        : DateTime.parse(event.endsAt).toLocal();
    _timezone = event?.timezone ?? widget.initialTimezone;
    _recurrence = event?.recurrenceKind ?? 'none';
    _priority = event?.priority ?? 'normal';
    _projectId = event?.projectId;
    _recurrenceInterval = event?.recurrenceInterval ?? 1;
    _recurrenceUntil = event?.recurrenceUntil == null
        ? null
        : DateTime.tryParse(event!.recurrenceUntil!);
  }

  @override
  void dispose() {
    _title.dispose();
    _description.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    backgroundColor: JackPalette.panel,
    title: Text(
      widget.event == null ? 'Nuovo appuntamento' : 'Modifica appuntamento',
    ),
    content: SizedBox(
      width: 480,
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: _title,
              autofocus: true,
              decoration: const InputDecoration(labelText: 'Titolo *'),
            ),
            TextField(
              controller: _description,
              maxLines: 2,
              decoration: const InputDecoration(labelText: 'Descrizione'),
            ),
            _DateTimePicker(
              label: 'Inizio',
              value: _startsAt,
              onChanged: (value) => setState(() => _startsAt = value),
            ),
            _DateTimePicker(
              label: 'Fine',
              value: _endsAt,
              onChanged: (value) => setState(() => _endsAt = value),
            ),
            DropdownMenu<String>(
              initialSelection: _timezone,
              expandedInsets: EdgeInsets.zero,
              enableFilter: true,
              requestFocusOnTap: true,
              label: const Text('Fuso orario'),
              dropdownMenuEntries: [
                for (final timezone in widget.timezones)
                  DropdownMenuEntry(value: timezone, label: timezone),
              ],
              onSelected: (value) {
                if (value != null) setState(() => _timezone = value);
              },
            ),
            DropdownButtonFormField<String?>(
              initialValue: _projectId,
              decoration: const InputDecoration(labelText: 'Progetto'),
              items: [
                const DropdownMenuItem(
                  value: null,
                  child: Text('Nessun progetto'),
                ),
                for (final project in widget.projects)
                  DropdownMenuItem(
                    value: project.id,
                    child: Text(project.name),
                  ),
              ],
              onChanged: (value) => setState(() => _projectId = value),
            ),
            DropdownButtonFormField<String>(
              initialValue: _priority,
              decoration: const InputDecoration(labelText: 'Priorità'),
              items: const [
                DropdownMenuItem(value: 'low', child: Text('Bassa')),
                DropdownMenuItem(value: 'normal', child: Text('Normale')),
                DropdownMenuItem(value: 'high', child: Text('Alta')),
                DropdownMenuItem(value: 'critical', child: Text('Critica')),
              ],
              onChanged: (value) =>
                  setState(() => _priority = value ?? 'normal'),
            ),
            DropdownButtonFormField<String>(
              initialValue: _recurrence,
              decoration: const InputDecoration(labelText: 'Ricorrenza'),
              items: const [
                DropdownMenuItem(value: 'none', child: Text('Nessuna')),
                DropdownMenuItem(value: 'daily', child: Text('Ogni giorno')),
                DropdownMenuItem(
                  value: 'weekly',
                  child: Text('Ogni settimana'),
                ),
                DropdownMenuItem(value: 'monthly', child: Text('Ogni mese')),
              ],
              onChanged: (value) =>
                  setState(() => _recurrence = value ?? 'none'),
            ),
            if (_recurrence != 'none') ...[
              TextFormField(
                initialValue: '$_recurrenceInterval',
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Intervallo ricorrenza',
                  helperText: 'Per esempio 2 = ogni due settimane',
                ),
                onChanged: (value) {
                  final parsed = int.tryParse(value);
                  if (parsed != null && parsed > 0) {
                    _recurrenceInterval = parsed;
                  }
                },
              ),
              TextButton.icon(
                onPressed: () async {
                  final value = await showDatePicker(
                    context: context,
                    initialDate:
                        _recurrenceUntil ??
                        _startsAt.add(const Duration(days: 30)),
                    firstDate: DateTime(2000),
                    lastDate: DateTime(2200),
                  );
                  if (value != null) {
                    setState(() => _recurrenceUntil = value);
                  }
                },
                icon: const Icon(Icons.event_repeat, size: 16),
                label: Text(
                  _recurrenceUntil == null
                      ? 'Fine ricorrenza (opzionale)'
                      : 'Fino al ${_dateOnly(_recurrenceUntil!)}',
                ),
              ),
            ],
          ],
        ),
      ),
    ),
    actions: [
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Annulla'),
      ),
      FilledButton(
        onPressed: () {
          if (_title.text.trim().isEmpty || !_endsAt.isAfter(_startsAt)) return;
          Navigator.pop(context, <String, Object?>{
            'title': _title.text.trim(),
            'description': _description.text.trim(),
            'starts_at': _localDateTime(_startsAt),
            'ends_at': _localDateTime(_endsAt),
            'timezone': _timezone,
            'priority': _priority,
            'project_id': _projectId,
            'recurrence_kind': _recurrence,
            'recurrence_interval': _recurrenceInterval,
            'recurrence_until': _recurrenceUntil == null
                ? null
                : _dateOnly(_recurrenceUntil!),
          });
        },
        child: const Text('Salva'),
      ),
    ],
  );
}

class _DateTimePicker extends StatelessWidget {
  const _DateTimePicker({
    required this.label,
    required this.value,
    required this.onChanged,
  });

  final String label;
  final DateTime value;
  final ValueChanged<DateTime> onChanged;

  @override
  Widget build(BuildContext context) => TextButton.icon(
    onPressed: () async {
      final day = await showDatePicker(
        context: context,
        initialDate: value,
        firstDate: DateTime(2000),
        lastDate: DateTime(2200),
      );
      if (day == null || !context.mounted) return;
      final time = await showTimePicker(
        context: context,
        initialTime: TimeOfDay.fromDateTime(value),
      );
      if (time == null) return;
      onChanged(DateTime(day.year, day.month, day.day, time.hour, time.minute));
    },
    icon: const Icon(Icons.schedule, size: 16),
    label: Text('$label · ${_dateOnly(value)} ${_time(value)}'),
  );
}

class _ViewButton extends StatelessWidget {
  const _ViewButton({
    required this.selected,
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final bool selected;
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => OutlinedButton.icon(
    onPressed: onTap,
    icon: Icon(icon, size: 15),
    label: Text(label),
    style: OutlinedButton.styleFrom(
      foregroundColor: selected ? JackPalette.amber : JackPalette.muted,
      side: BorderSide(
        color: selected ? JackPalette.amberSoft : JackPalette.border,
      ),
      visualDensity: VisualDensity.compact,
    ),
  );
}

class _ScaleSelector extends StatelessWidget {
  const _ScaleSelector({required this.value, required this.onChanged});

  final _CalendarScale value;
  final ValueChanged<_CalendarScale> onChanged;

  @override
  Widget build(BuildContext context) => SegmentedButton<_CalendarScale>(
    segments: const [
      ButtonSegment(value: _CalendarScale.day, label: Text('Giorno')),
      ButtonSegment(value: _CalendarScale.week, label: Text('Settimana')),
      ButtonSegment(value: _CalendarScale.month, label: Text('Mese')),
    ],
    selected: {value},
    onSelectionChanged: (selection) => onChanged(selection.first),
    showSelectedIcon: false,
  );
}

class _CalendarDayCell extends StatelessWidget {
  const _CalendarDayCell({
    required this.date,
    required this.selected,
    required this.count,
    required this.onTap,
  });

  final DateTime date;
  final bool selected;
  final int count;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
    onTap: onTap,
    borderRadius: BorderRadius.circular(9),
    child: Container(
      margin: const EdgeInsets.all(2),
      decoration: BoxDecoration(
        color: selected ? JackPalette.amber.withValues(alpha: 0.13) : null,
        borderRadius: BorderRadius.circular(9),
        border: Border.all(
          color: selected ? JackPalette.amberSoft : JackPalette.borderSoft,
        ),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            '${date.day}',
            style: TextStyle(
              color: selected ? JackPalette.amber : JackPalette.text,
            ),
          ),
          if (count > 0)
            Text(
              '$count elementi',
              style: const TextStyle(color: JackPalette.dim, fontSize: 8),
            ),
        ],
      ),
    ),
  );
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.title, this.trailing});

  final String title;
  final String? trailing;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(2, 8, 2, 7),
    child: Row(
      children: [
        Expanded(child: SectionEyebrow(title)),
        if (trailing != null)
          Text(
            trailing!,
            style: const TextStyle(color: JackPalette.dim, fontSize: 10),
          ),
      ],
    ),
  );
}

class _Metric extends StatelessWidget {
  const _Metric({
    required this.value,
    required this.label,
    this.color = JackPalette.text,
  });

  final String value;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        value,
        style: TextStyle(
          color: color,
          fontSize: 22,
          fontWeight: FontWeight.w300,
        ),
      ),
      const SizedBox(height: 3),
      Text(
        label,
        style: const TextStyle(
          color: JackPalette.dim,
          fontSize: 8,
          letterSpacing: 1,
        ),
      ),
    ],
  );
}

class _PriorityDot extends StatelessWidget {
  const _PriorityDot({required this.priority});

  final String priority;

  @override
  Widget build(BuildContext context) => StatusDot(
    color: switch (priority) {
      'critical' => JackPalette.red,
      'high' => JackPalette.amber,
      'low' => JackPalette.blue,
      _ => JackPalette.dim,
    },
    size: 6,
  );
}

class _ProgressIndicator extends StatelessWidget {
  const _ProgressIndicator({required this.percent});

  final int percent;

  @override
  Widget build(BuildContext context) => ClipRRect(
    borderRadius: BorderRadius.circular(4),
    child: LinearProgressIndicator(
      value: percent / 100,
      minHeight: 5,
      color: JackPalette.cyan,
      backgroundColor: JackPalette.panelRaised,
    ),
  );
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  final IconData icon;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 44, horizontal: 18),
    child: Column(
      children: [
        Icon(icon, color: JackPalette.cyan, size: 26),
        const SizedBox(height: 10),
        Text(title, style: const TextStyle(fontSize: 14)),
        const SizedBox(height: 5),
        Text(
          subtitle,
          textAlign: TextAlign.center,
          style: const TextStyle(color: JackPalette.muted, fontSize: 11),
        ),
      ],
    ),
  );
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => _EmptyState(
    icon: Icons.cloud_off_outlined,
    title: 'Pianificazione non disponibile',
    subtitle: message,
  );
}

String _statusLabel(String status) => switch (status) {
  'inbox' => 'Inbox',
  'todo' => 'Da fare',
  'in_progress' => 'In corso',
  'blocked' => 'Bloccata',
  'completed' => 'Completata',
  'cancelled' => 'Annullata',
  _ => status,
};

String _priorityLabel(String priority) => switch (priority) {
  'low' => 'Bassa',
  'normal' => 'Normale',
  'high' => 'Alta',
  'critical' => 'Critica',
  _ => priority,
};

String _projectStatusLabel(String status) => switch (status) {
  'active' => 'Attivo',
  'on_hold' => 'In pausa',
  'completed' => 'Completato',
  'archived' => 'Archiviato',
  _ => status,
};

String _missionStatusLabel(String status) => switch (status) {
  'planned' => 'Pianificata',
  'pending_approval' => 'In attesa di approvazione',
  'approved' => 'Approvata',
  'cancelled' => 'Annullata',
  _ => status,
};

String _dateOnly(DateTime date) =>
    '${date.year.toString().padLeft(4, '0')}-'
    '${date.month.toString().padLeft(2, '0')}-'
    '${date.day.toString().padLeft(2, '0')}';

String _time(DateTime date) =>
    '${date.hour.toString().padLeft(2, '0')}:'
    '${date.minute.toString().padLeft(2, '0')}';

String _localDateTime(DateTime date) => '${_dateOnly(date)}T${_time(date)}:00';

String _formatDate(DateTime date) =>
    '${date.day.toString().padLeft(2, '0')}/'
    '${date.month.toString().padLeft(2, '0')}/${date.year}';

String _rangeLabel((DateTime, DateTime) range) =>
    '${_formatDate(range.$1)} – ${_formatDate(range.$2)}';
