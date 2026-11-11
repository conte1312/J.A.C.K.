/// Presentation data for the Agency screen.
///
/// Names, divisions and short descriptions are taken from the upstream
/// `msitarzewski/agency-agents` catalog (MIT, pinned commit
/// b859c515d813efcfc4755d3471dd9e7686c7706d). This is a preview only: the
/// full catalog import happens in M6 and no agent is operative.
library;

class DemoAgencyDivision {
  const DemoAgencyDivision({required this.name, required this.count});

  final String name;
  final int count;
}

const List<DemoAgencyDivision> demoAgencyDivisions = <DemoAgencyDivision>[
  DemoAgencyDivision(name: 'Academic', count: 6),
  DemoAgencyDivision(name: 'Design', count: 10),
  DemoAgencyDivision(name: 'Engineering', count: 66),
  DemoAgencyDivision(name: 'Finance', count: 5),
  DemoAgencyDivision(name: 'Game Development', count: 6),
  DemoAgencyDivision(name: 'GIS', count: 13),
  DemoAgencyDivision(name: 'Healthcare', count: 3),
  DemoAgencyDivision(name: 'Integrations', count: 1),
  DemoAgencyDivision(name: 'Marketing', count: 37),
  DemoAgencyDivision(name: 'Paid Media', count: 7),
  DemoAgencyDivision(name: 'Product', count: 6),
  DemoAgencyDivision(name: 'Project Management', count: 7),
  DemoAgencyDivision(name: 'Research', count: 1),
  DemoAgencyDivision(name: 'Sales', count: 9),
  DemoAgencyDivision(name: 'Security', count: 12),
  DemoAgencyDivision(name: 'Spatial Computing', count: 6),
  DemoAgencyDivision(name: 'Specialized', count: 59),
  DemoAgencyDivision(name: 'Strategy', count: 3),
  DemoAgencyDivision(name: 'Support', count: 6),
  DemoAgencyDivision(name: 'Testing', count: 9),
];

const int demoAgencyTotalProfiles = 272;

class DemoAgencyAgent {
  const DemoAgencyAgent({
    required this.id,
    required this.name,
    required this.division,
    required this.description,
    required this.skills,
  });

  final String id;
  final String name;
  final String division;
  final String description;
  final List<String> skills;
}

const List<DemoAgencyAgent> demoAgencyAgents = <DemoAgencyAgent>[
  DemoAgencyAgent(
    id: 'engineering-backend-architect',
    name: 'Backend Architect',
    division: 'Engineering',
    description: 'Senior backend architect specializing in scalable system design, database architecture, API development and cloud infrastructure.',
    skills: <String>['Architettura', 'API', 'Database', 'Cloud'],
  ),
  DemoAgencyAgent(
    id: 'engineering-frontend-developer',
    name: 'Frontend Developer',
    division: 'Engineering',
    description: 'Expert frontend developer specializing in modern UI implementation, component architecture and performance optimization.',
    skills: <String>['UI', 'Componenti', 'Performance'],
  ),
  DemoAgencyAgent(
    id: 'engineering-data-engineer',
    name: 'Data Engineer',
    division: 'Engineering',
    description: 'Expert data engineer specializing in reliable data pipelines, lakehouse architectures and scalable data infrastructure.',
    skills: <String>['Pipeline', 'ETL', 'Dati'],
  ),
  DemoAgencyAgent(
    id: 'engineering-mobile-app-builder',
    name: 'Mobile App Builder',
    division: 'Engineering',
    description: 'Specialized mobile application developer with expertise in native iOS/Android development and cross-platform frameworks.',
    skills: <String>['iOS', 'Android', 'Cross-platform'],
  ),
  DemoAgencyAgent(
    id: 'design-ui-designer',
    name: 'UI Designer',
    division: 'Design',
    description: 'Expert UI designer specializing in visual design systems, component libraries and accessible, pixel-perfect interfaces.',
    skills: <String>['Design system', 'Componenti', 'Accessibilità'],
  ),
  DemoAgencyAgent(
    id: 'design-ux-researcher',
    name: 'UX Researcher',
    division: 'Design',
    description: 'Expert user experience researcher specializing in user behavior analysis, usability testing and data-driven design insights.',
    skills: <String>['Ricerca', 'Usability', 'Insight'],
  ),
  DemoAgencyAgent(
    id: 'product-product-manager',
    name: 'Product Manager',
    division: 'Product',
    description: 'Holistic product leader who owns the full product lifecycle, from discovery and strategy through roadmap and outcome measurement.',
    skills: <String>['Roadmap', 'Strategia', 'Discovery'],
  ),
  DemoAgencyAgent(
    id: 'marketing-growth-hacker',
    name: 'Growth Hacker',
    division: 'Marketing',
    description: 'Expert growth strategist specializing in rapid user acquisition through data-driven experimentation and scalable growth channels.',
    skills: <String>['Crescita', 'Esperimenti', 'Funnel'],
  ),
  DemoAgencyAgent(
    id: 'marketing-content-creator',
    name: 'Content Creator',
    division: 'Marketing',
    description: 'Expert content strategist and creator for multi-platform campaigns, editorial calendars and brand storytelling.',
    skills: <String>['Editoriale', 'Copy', 'Brand'],
  ),
  DemoAgencyAgent(
    id: 'project-management-project-shepherd',
    name: 'Project Shepherd',
    division: 'Project Management',
    description: 'Expert project manager specializing in cross-functional coordination, timeline management and stakeholder alignment.',
    skills: <String>['Coordinamento', 'Timeline', 'Rischi'],
  ),
  DemoAgencyAgent(
    id: 'testing-api-tester',
    name: 'API Tester',
    division: 'Testing',
    description: 'Expert API testing specialist focused on comprehensive validation, performance testing and quality assurance.',
    skills: <String>['API testing', 'Performance', 'Qualità'],
  ),
  DemoAgencyAgent(
    id: 'support-support-responder',
    name: 'Support Responder',
    division: 'Support',
    description: 'Expert customer support specialist delivering issue resolution, multi-channel support and proactive customer care.',
    skills: <String>['Supporto', 'Triage', 'Customer care'],
  ),
  DemoAgencyAgent(
    id: 'sales-deal-strategist',
    name: 'Deal Strategist',
    division: 'Sales',
    description: 'Senior deal strategist specializing in qualification, competitive positioning and win planning for complex B2B sales cycles.',
    skills: <String>['Qualifica', 'Strategia', 'B2B'],
  ),
  DemoAgencyAgent(
    id: 'finance-financial-analyst',
    name: 'Financial Analyst',
    division: 'Finance',
    description: 'Expert financial analyst specializing in modeling, forecasting, scenario analysis and data-driven decision support.',
    skills: <String>['Modelli', 'Forecast', 'Analisi'],
  ),
];
