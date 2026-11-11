/// The ten navigable sections of J.A.C.K. 2.0.
library;

import 'package:flutter/material.dart';

import '../design_system/tokens.dart';

/// Sidebar groups.
enum JackNavGroup {
  workspace('Spazio di lavoro'),
  systems('Sistemi'),
  configuration('Configurazione');

  const JackNavGroup(this.label);

  final String label;
}

/// A top-level destination in the application shell.
enum JackDestination {
  conversations(
    slug: 'conversations',
    title: 'Conversazioni',
    shortLabel: 'Conversazioni',
    description: 'Riprendi il filo delle conversazioni e del contesto.',
    icon: JackIcons.conversations,
    group: JackNavGroup.workspace,
  ),
  memory(
    slug: 'memory',
    title: 'Memoria',
    shortLabel: 'Memoria',
    description: 'Ricordi, categorie e knowledge graph.',
    icon: JackIcons.memory,
    group: JackNavGroup.workspace,
  ),
  exploration(
    slug: 'exploration',
    title: 'Esplorazione',
    shortLabel: 'Esplorazione',
    description: 'Mappa visiva di memorie e collegamenti.',
    icon: JackIcons.exploration,
    group: JackNavGroup.workspace,
  ),
  planning(
    slug: 'planning',
    title: 'Pianificazione e Attività',
    shortLabel: 'Pianificazione',
    description: 'Task, progetti, priorità e calendario.',
    icon: JackIcons.planning,
    group: JackNavGroup.workspace,
  ),
  modules(
    slug: 'modules',
    title: 'Moduli',
    shortLabel: 'Moduli',
    description: 'Catalogo delle capacità e degli strumenti di J.A.C.K.',
    icon: JackIcons.modules,
    group: JackNavGroup.systems,
  ),
  aiHub(
    slug: 'ai-hub',
    title: 'AI Hub',
    shortLabel: 'AI Hub',
    description: 'Provider, modelli e routing.',
    icon: JackIcons.aiHub,
    group: JackNavGroup.systems,
  ),
  agency(
    slug: 'agency',
    title: 'Agency',
    shortLabel: 'Agency',
    description: 'Catalogo agenti e composizione del team.',
    icon: JackIcons.agency,
    group: JackNavGroup.systems,
  ),
  settings(
    slug: 'settings',
    title: 'Impostazioni',
    shortLabel: 'Impostazioni',
    description: 'Preferenze, privacy e configurazione.',
    icon: JackIcons.settings,
    group: JackNavGroup.configuration,
  ),
  profile(
    slug: 'profile',
    title: 'Profilo e Account',
    shortLabel: 'Profilo',
    description: 'Profilo locale, preferenze personali e sicurezza.',
    icon: JackIcons.profile,
    group: JackNavGroup.configuration,
  ),
  systemStatus(
    slug: 'system-status',
    title: 'Stato del sistema',
    shortLabel: 'Stato sistema',
    description: 'Backend, servizi e diagnostica.',
    icon: JackIcons.systemStatus,
    group: JackNavGroup.configuration,
  );

  const JackDestination({
    required this.slug,
    required this.title,
    required this.shortLabel,
    required this.description,
    required this.icon,
    required this.group,
  });

  final String slug;
  final String title;
  final String shortLabel;
  final String description;
  final IconData icon;
  final JackNavGroup group;

  Key get screenKey => Key('screen-$slug');
  Key get navKey => Key('nav-$slug');
}
