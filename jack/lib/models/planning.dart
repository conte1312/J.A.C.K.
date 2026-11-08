class PlanningTask {
  const PlanningTask({
    required this.id,
    required this.title,
    required this.status,
    required this.priority,
    this.description = '',
    this.createdAt,
    this.completedAt,
    this.category = '',
    this.tags = const [],
    this.startDate,
    this.dueDate,
    this.projectId,
    this.missionId,
    this.recurrenceKind = 'none',
    this.recurrenceInterval = 1,
    this.notes = '',
    this.aiOrigin = false,
    this.responsibleAgent,
    this.checklist = const [],
    this.dependencies = const [],
  });

  final String id;
  final String title;
  final String status;
  final String priority;
  final String description;
  final String? createdAt;
  final String? completedAt;
  final String category;
  final List<String> tags;
  final String? startDate;
  final String? dueDate;
  final String? projectId;
  final String? missionId;
  final String recurrenceKind;
  final int recurrenceInterval;
  final String notes;
  final bool aiOrigin;
  final String? responsibleAgent;
  final List<PlanningChecklistItem> checklist;
  final List<Map<String, dynamic>> dependencies;

  factory PlanningTask.fromJson(Map<String, dynamic> json) => PlanningTask(
    id: json['id'] as String,
    title: json['title'] as String,
    status: json['status'] as String,
    priority: json['priority'] as String,
    description: json['description'] as String? ?? '',
    createdAt: json['created_at'] as String?,
    completedAt: json['completed_at'] as String?,
    category: json['category'] as String? ?? '',
    tags: (json['tags'] as List<dynamic>? ?? const []).cast<String>(),
    startDate: json['start_date'] as String?,
    dueDate: json['due_date'] as String?,
    projectId: json['project_id'] as String?,
    missionId: json['mission_id'] as String?,
    recurrenceKind: json['recurrence_kind'] as String? ?? 'none',
    recurrenceInterval: json['recurrence_interval'] as int? ?? 1,
    notes: json['notes'] as String? ?? '',
    aiOrigin: json['ai_origin'] == true || json['ai_origin'] == 1,
    responsibleAgent: json['responsible_agent'] as String?,
    checklist: (json['checklist'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(PlanningChecklistItem.fromJson)
        .toList(growable: false),
    dependencies: (json['dependencies'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .toList(growable: false),
  );
}

class PlanningChecklistItem {
  const PlanningChecklistItem({
    required this.id,
    required this.title,
    required this.isDone,
  });

  final String id;
  final String title;
  final bool isDone;

  factory PlanningChecklistItem.fromJson(Map<String, dynamic> json) =>
      PlanningChecklistItem(
        id: json['id'] as String,
        title: json['title'] as String,
        isDone: json['is_done'] == true || json['is_done'] == 1,
      );
}

class PlanningProject {
  const PlanningProject({
    required this.id,
    required this.name,
    required this.status,
    required this.priority,
    required this.completionPercent,
    required this.openTaskCount,
    required this.completedTaskCount,
    this.description = '',
    this.goal = '',
    this.startDate,
    this.dueDate,
    this.notes = '',
    this.milestones = const [],
  });

  final String id;
  final String name;
  final String status;
  final String priority;
  final int completionPercent;
  final int openTaskCount;
  final int completedTaskCount;
  final String description;
  final String goal;
  final String? startDate;
  final String? dueDate;
  final String notes;
  final List<ProjectMilestone> milestones;

  factory PlanningProject.fromJson(Map<String, dynamic> json) =>
      PlanningProject(
        id: json['id'] as String,
        name: json['name'] as String,
        status: json['status'] as String? ?? 'active',
        priority: json['priority'] as String? ?? 'normal',
        completionPercent: json['completion_percent'] as int? ?? 0,
        openTaskCount: json['open_task_count'] as int? ?? 0,
        completedTaskCount: json['completed_task_count'] as int? ?? 0,
        description: json['description'] as String? ?? '',
        goal: json['goal'] as String? ?? '',
        startDate: json['start_date'] as String?,
        dueDate: json['due_date'] as String?,
        notes: json['notes'] as String? ?? '',
        milestones: (json['milestones'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(ProjectMilestone.fromJson)
            .toList(growable: false),
      );
}

class ProjectMilestone {
  const ProjectMilestone({
    required this.id,
    required this.title,
    this.description = '',
    this.dueDate,
    this.completedAt,
  });

  final String id;
  final String title;
  final String description;
  final String? dueDate;
  final String? completedAt;

  bool get isCompleted => completedAt != null;

  factory ProjectMilestone.fromJson(Map<String, dynamic> json) =>
      ProjectMilestone(
        id: json['id'] as String,
        title: json['title'] as String,
        description: json['description'] as String? ?? '',
        dueDate: json['due_date'] as String?,
        completedAt: json['completed_at'] as String?,
      );
}

class PlanningEvent {
  const PlanningEvent({
    required this.id,
    required this.title,
    required this.startsAt,
    required this.endsAt,
    required this.timezone,
    required this.priority,
    this.description = '',
    this.projectId,
    this.recurrenceKind = 'none',
    this.recurrenceInterval = 1,
    this.recurrenceUntil,
    this.occurrenceStartsAt,
    this.occurrenceEndsAt,
  });

  final String id;
  final String title;
  final String startsAt;
  final String endsAt;
  final String timezone;
  final String priority;
  final String description;
  final String? projectId;
  final String recurrenceKind;
  final int recurrenceInterval;
  final String? recurrenceUntil;
  final String? occurrenceStartsAt;
  final String? occurrenceEndsAt;

  factory PlanningEvent.fromJson(Map<String, dynamic> json) => PlanningEvent(
    id: json['id'] as String,
    title: json['title'] as String,
    startsAt: json['starts_at'] as String,
    endsAt: json['ends_at'] as String,
    timezone: json['timezone'] as String,
    priority: json['priority'] as String? ?? 'normal',
    description: json['description'] as String? ?? '',
    projectId: json['project_id'] as String?,
    recurrenceKind: json['recurrence_kind'] as String? ?? 'none',
    recurrenceInterval: json['recurrence_interval'] as int? ?? 1,
    recurrenceUntil: json['recurrence_until'] as String?,
    occurrenceStartsAt: json['occurrence_starts_at'] as String?,
    occurrenceEndsAt: json['occurrence_ends_at'] as String?,
  );
}

class PlanningMission {
  const PlanningMission({
    required this.id,
    required this.title,
    required this.status,
    required this.progressPercent,
    this.description = '',
    this.plan = '',
    this.assignedAgents = const [],
    this.results = '',
    this.notes = '',
    this.taskIds = const [],
    this.logs = const [],
    this.approvals = const [],
  });

  final String id;
  final String title;
  final String status;
  final int progressPercent;
  final String description;
  final String plan;
  final List<String> assignedAgents;
  final String results;
  final String notes;
  final List<String> taskIds;
  final List<PlanningMissionLog> logs;
  final List<PlanningMissionApproval> approvals;

  factory PlanningMission.fromJson(Map<String, dynamic> json) =>
      PlanningMission(
        id: json['id'] as String,
        title: json['title'] as String,
        status: json['status'] as String? ?? 'planned',
        progressPercent: json['progress_percent'] as int? ?? 0,
        description: json['description'] as String? ?? '',
        plan: json['plan'] as String? ?? '',
        assignedAgents: (json['assigned_agents'] as List<dynamic>? ?? const [])
            .cast<String>(),
        results: json['results'] as String? ?? '',
        notes: json['notes'] as String? ?? '',
        taskIds: (json['task_ids'] as List<dynamic>? ?? const []).cast<String>(),
        logs: (json['logs'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(PlanningMissionLog.fromJson)
            .toList(growable: false),
        approvals: (json['approvals'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(PlanningMissionApproval.fromJson)
            .toList(growable: false),
      );
}

class PlanningMissionLog {
  const PlanningMissionLog({
    required this.id,
    required this.message,
    required this.createdAt,
  });

  final String id;
  final String message;
  final String createdAt;

  factory PlanningMissionLog.fromJson(Map<String, dynamic> json) =>
      PlanningMissionLog(
        id: json['id'] as String,
        message: json['message'] as String,
        createdAt: json['created_at'] as String,
      );
}

class PlanningMissionApproval {
  const PlanningMissionApproval({
    required this.id,
    required this.description,
    required this.status,
  });

  final String id;
  final String description;
  final String status;

  factory PlanningMissionApproval.fromJson(Map<String, dynamic> json) =>
      PlanningMissionApproval(
        id: json['id'] as String,
        description: json['description'] as String,
        status: json['status'] as String,
      );
}

class PlanningAiProposal {
  const PlanningAiProposal({
    required this.understood,
    required this.message,
    required this.operations,
    this.proposalId,
  });

  final bool understood;
  final String message;
  final String? proposalId;
  final List<Map<String, dynamic>> operations;

  factory PlanningAiProposal.fromJson(Map<String, dynamic> json) =>
      PlanningAiProposal(
        understood: json['understood'] as bool? ?? false,
        message: json['message'] as String? ?? '',
        proposalId: json['proposal_id'] as String?,
        operations: (json['operations'] as List<dynamic>? ?? const [])
            .whereType<Map<String, dynamic>>()
            .toList(growable: false),
      );
}

class PlanningCalendar {
  const PlanningCalendar({
    required this.tasks,
    required this.events,
    required this.timezone,
  });

  final List<PlanningTask> tasks;
  final List<PlanningEvent> events;
  final String timezone;
}
