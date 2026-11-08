import '../models/planning.dart';
import 'local_api_client.dart';

abstract interface class PlanningGateway {
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
  });

  Future<PlanningTask> createTask(Map<String, Object?> draft);
  Future<PlanningTask> updateTask(String id, Map<String, Object?> patch);
  Future<PlanningTask> completeTask(String id);
  Future<void> deleteTask(String id);
  Future<PlanningChecklistItem> addChecklistItem(String taskId, String title);
  Future<PlanningChecklistItem> updateChecklistItem(
    String id,
    Map<String, Object?> patch,
  );
  Future<void> deleteChecklistItem(String id);
  Future<void> addDependency(String taskId, String prerequisiteTaskId);
  Future<void> removeDependency(String dependencyId);

  Future<List<PlanningProject>> listProjects({String? query});
  Future<List<PlanningMission>> listMissions({String? status});
  Future<PlanningMission> createMission(Map<String, Object?> draft);
  Future<PlanningMission> updateMission(String id, Map<String, Object?> patch);
  Future<void> deleteMission(String id);
  Future<PlanningMissionLog> addMissionLog(String id, String message);
  Future<PlanningMissionApproval> createMissionApproval(
    String id,
    String description,
  );
  Future<PlanningMissionApproval> updateMissionApproval(
    String id,
    String status,
  );
  Future<PlanningProject> createProject(Map<String, Object?> draft);
  Future<PlanningProject> updateProject(String id, Map<String, Object?> patch);
  Future<PlanningProject> archiveProject(String id);
  Future<void> deleteProject(String id);
  Future<ProjectMilestone> createMilestone(
    String projectId,
    Map<String, Object?> draft,
  );
  Future<ProjectMilestone> updateMilestone(
    String id,
    Map<String, Object?> patch,
  );
  Future<void> deleteMilestone(String id);

  Future<PlanningCalendar> getCalendar({
    required DateTime from,
    required DateTime to,
    required String timezone,
    String? projectId,
    String? priority,
  });
  Future<List<String>> listTimezones();
  Future<PlanningEvent> createEvent(Map<String, Object?> draft);
  Future<PlanningEvent> updateEvent(String id, Map<String, Object?> patch);
  Future<void> deleteEvent(String id);

  Future<PlanningAiProposal> interpret(String text);
  Future<List<Map<String, dynamic>>> applyProposal({
    required String proposalId,
    required bool confirmed,
  });
}

class PlanningApiService implements PlanningGateway {
  PlanningApiService({LocalApiClient? client})
    : _client = client ?? LocalApiClient();

  final LocalApiClient _client;
  static const _prefix = '/api/v1/planning';

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
  }) async {
    final params = <String, String>{};
    if (query?.trim().isNotEmpty ?? false) params['query'] = query!.trim();
    if (status != null) params['status'] = status;
    if (priority != null) params['priority'] = priority;
    if (projectId != null) params['project_id'] = projectId;
    if (missionId != null) params['mission_id'] = missionId;
    if (category != null) params['category'] = category;
    if (tag != null) params['tag'] = tag;
    if (dueAfter != null) params['due_after'] = dueAfter;
    if (dueBefore != null) params['due_before'] = dueBefore;
    if (sort != null) params['sort'] = sort;
    if (descending) params['descending'] = 'true';
    if (overdueOnly) params['overdue_only'] = 'true';
    final response = await _client.getJson(
      '$_prefix/tasks',
      queryParameters: params,
    );
    if (response is! List) {
      throw const FormatException('Elenco attività non valido.');
    }
    return response.map(_taskFrom).toList(growable: false);
  }

  @override
  Future<PlanningTask> createTask(Map<String, Object?> draft) async =>
      _taskFrom(await _client.postJson('$_prefix/tasks', draft));

  @override
  Future<PlanningTask> updateTask(
    String id,
    Map<String, Object?> patch,
  ) async => _taskFrom(await _client.putJson('$_prefix/tasks/$id', patch));

  @override
  Future<PlanningTask> completeTask(String id) async => _taskFrom(
    await _client.postJson('$_prefix/tasks/$id/complete', const {}),
  );

  @override
  Future<void> deleteTask(String id) => _client.delete('$_prefix/tasks/$id');

  @override
  Future<PlanningChecklistItem> addChecklistItem(
    String taskId,
    String title,
  ) async => _checklistFrom(
    await _client.postJson('$_prefix/tasks/$taskId/checklist', {
      'title': title,
    }),
  );

  @override
  Future<PlanningChecklistItem> updateChecklistItem(
    String id,
    Map<String, Object?> patch,
  ) async =>
      _checklistFrom(await _client.putJson('$_prefix/checklist/$id', patch));

  @override
  Future<void> deleteChecklistItem(String id) =>
      _client.delete('$_prefix/checklist/$id');

  @override
  Future<void> addDependency(String taskId, String prerequisiteTaskId) async {
    await _client.postJson('$_prefix/tasks/$taskId/dependencies', {
      'depends_on_task_id': prerequisiteTaskId,
    });
  }

  @override
  Future<void> removeDependency(String dependencyId) =>
      _client.delete('$_prefix/dependencies/$dependencyId');

  @override
  Future<List<PlanningProject>> listProjects({String? query}) async {
    final response = await _client.getJson(
      '$_prefix/projects',
      queryParameters: query == null ? null : {'query': query},
    );
    if (response is! List) {
      throw const FormatException('Elenco progetti non valido.');
    }
    return response.map(_projectFrom).toList(growable: false);
  }

  @override
  Future<List<PlanningMission>> listMissions({String? status}) async {
    final response = await _client.getJson(
      '$_prefix/missions',
      queryParameters: status == null ? null : {'status': status},
    );
    if (response is! List) {
      throw const FormatException('Elenco missioni non valido.');
    }
    return response.map(_missionFrom).toList(growable: false);
  }

  @override
  Future<PlanningMission> createMission(Map<String, Object?> draft) async =>
      _missionFrom(await _client.postJson('$_prefix/missions', draft));

  @override
  Future<PlanningMission> updateMission(
    String id,
    Map<String, Object?> patch,
  ) async =>
      _missionFrom(await _client.putJson('$_prefix/missions/$id', patch));

  @override
  Future<void> deleteMission(String id) =>
      _client.delete('$_prefix/missions/$id');

  @override
  Future<PlanningMissionLog> addMissionLog(String id, String message) async =>
      _missionLogFrom(
        await _client.postJson('$_prefix/missions/$id/logs', {
          'message': message,
        }),
      );

  @override
  Future<PlanningMissionApproval> createMissionApproval(
    String id,
    String description,
  ) async => _missionApprovalFrom(
    await _client.postJson('$_prefix/missions/$id/approvals', {
      'description': description,
    }),
  );

  @override
  Future<PlanningMissionApproval> updateMissionApproval(
    String id,
    String status,
  ) async => _missionApprovalFrom(
    await _client.putJson('$_prefix/mission-approvals/$id', {'status': status}),
  );

  @override
  Future<PlanningProject> createProject(Map<String, Object?> draft) async =>
      _projectFrom(await _client.postJson('$_prefix/projects', draft));

  @override
  Future<PlanningProject> updateProject(
    String id,
    Map<String, Object?> patch,
  ) async =>
      _projectFrom(await _client.putJson('$_prefix/projects/$id', patch));

  @override
  Future<PlanningProject> archiveProject(String id) async => _projectFrom(
    await _client.postJson('$_prefix/projects/$id/archive', const {}),
  );

  @override
  Future<void> deleteProject(String id) =>
      _client.delete('$_prefix/projects/$id');

  @override
  Future<ProjectMilestone> createMilestone(
    String projectId,
    Map<String, Object?> draft,
  ) async => _milestoneFrom(
    await _client.postJson('$_prefix/projects/$projectId/milestones', draft),
  );

  @override
  Future<ProjectMilestone> updateMilestone(
    String id,
    Map<String, Object?> patch,
  ) async =>
      _milestoneFrom(await _client.putJson('$_prefix/milestones/$id', patch));

  @override
  Future<void> deleteMilestone(String id) =>
      _client.delete('$_prefix/milestones/$id');

  @override
  Future<PlanningCalendar> getCalendar({
    required DateTime from,
    required DateTime to,
    required String timezone,
    String? projectId,
    String? priority,
  }) async {
    final response = await _client.getJson(
      '$_prefix/calendar',
      queryParameters: {
        'from_date': _dateOnly(from),
        'to_date': _dateOnly(to),
        'timezone': timezone,
        'project_id': ?projectId,
        'priority': ?priority,
      },
    );
    if (response is! Map<String, dynamic>) {
      throw const FormatException('Calendario non valido.');
    }
    final tasks = response['tasks'];
    final events = response['events'];
    if (tasks is! List || events is! List) {
      throw const FormatException('Dati calendario non validi.');
    }
    return PlanningCalendar(
      tasks: tasks.map(_taskFrom).toList(growable: false),
      events: events.map(_eventFrom).toList(growable: false),
      timezone: response['timezone'] as String? ?? timezone,
    );
  }

  @override
  Future<List<String>> listTimezones() async {
    final response = await _client.getJson('/api/v1/system/timezones');
    if (response is! Map<String, dynamic> ||
        response['timezones'] is! List<dynamic>) {
      throw const FormatException('Elenco fusi orari non valido.');
    }
    return (response['timezones'] as List<dynamic>).whereType<String>().toList(
      growable: false,
    );
  }

  @override
  Future<PlanningEvent> createEvent(Map<String, Object?> draft) async =>
      _eventFrom(await _client.postJson('$_prefix/calendar/events', draft));

  @override
  Future<PlanningEvent> updateEvent(
    String id,
    Map<String, Object?> patch,
  ) async =>
      _eventFrom(await _client.putJson('$_prefix/calendar/events/$id', patch));

  @override
  Future<void> deleteEvent(String id) =>
      _client.delete('$_prefix/calendar/events/$id');

  @override
  Future<PlanningAiProposal> interpret(String text) async {
    final response = await _client.postJson('$_prefix/ai/interpret', {
      'text': text,
    });
    if (response is! Map<String, dynamic>) {
      throw const FormatException('Proposta di pianificazione non valida.');
    }
    return PlanningAiProposal.fromJson(response);
  }

  @override
  Future<List<Map<String, dynamic>>> applyProposal({
    required String proposalId,
    required bool confirmed,
  }) async {
    final response = await _client.postJson('$_prefix/ai/apply', {
      'proposal_id': proposalId,
      'confirmed': confirmed,
    });
    if (response is! List) {
      throw const FormatException('Risultato della proposta non valido.');
    }
    return response.whereType<Map<String, dynamic>>().toList(growable: false);
  }

  PlanningTask _taskFrom(Object? value) {
    if (value is! Map<String, dynamic>) {
      throw const FormatException('Dati attività non validi.');
    }
    return PlanningTask.fromJson(value);
  }

  PlanningProject _projectFrom(Object? value) {
    if (value is! Map<String, dynamic>) {
      throw const FormatException('Dati progetto non validi.');
    }
    return PlanningProject.fromJson(value);
  }

  PlanningMission _missionFrom(Object? value) {
    if (value is! Map<String, dynamic>) {
      throw const FormatException('Dati missione non validi.');
    }
    return PlanningMission.fromJson(value);
  }

  PlanningMissionLog _missionLogFrom(Object? value) {
    if (value is! Map<String, dynamic>) {
      throw const FormatException('Log missione non valido.');
    }
    return PlanningMissionLog.fromJson(value);
  }

  PlanningMissionApproval _missionApprovalFrom(Object? value) {
    if (value is! Map<String, dynamic>) {
      throw const FormatException('Approvazione missione non valida.');
    }
    return PlanningMissionApproval.fromJson(value);
  }

  ProjectMilestone _milestoneFrom(Object? value) {
    if (value is! Map<String, dynamic>) {
      throw const FormatException('Dati milestone non validi.');
    }
    return ProjectMilestone.fromJson(value);
  }

  PlanningChecklistItem _checklistFrom(Object? value) {
    if (value is! Map<String, dynamic>) {
      throw const FormatException('Dati checklist non validi.');
    }
    return PlanningChecklistItem.fromJson(value);
  }

  PlanningEvent _eventFrom(Object? value) {
    if (value is! Map<String, dynamic>) {
      throw const FormatException('Dati evento non validi.');
    }
    return PlanningEvent.fromJson(value);
  }

  String _dateOnly(DateTime value) =>
      '${value.year.toString().padLeft(4, '0')}-'
      '${value.month.toString().padLeft(2, '0')}-'
      '${value.day.toString().padLeft(2, '0')}';
}
