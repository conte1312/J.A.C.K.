import 'package:flutter/material.dart';

enum JackSection {
  conversations(
    'Conversazioni',
    Icons.chat_bubble_outline_rounded,
    'Riprendi le conversazioni e visualizza il contesto dimostrativo.',
  ),
  memory(
    'Memoria',
    Icons.hub_outlined,
    'Consulta i nodi e le categorie di memoria di esempio.',
  ),
  planning(
    'Pianificazione',
    Icons.route_outlined,
    'Attività e promemoria sono anteprime non collegate.',
  ),
  modules(
    'Moduli',
    Icons.widgets_outlined,
    'I moduli locali non sono collegati in questa milestone.',
  ),
  settings(
    'Impostazioni',
    Icons.tune_rounded,
    'Le preferenze dell’app saranno configurabili qui.',
  ),
  exploration(
    'Esplorazione',
    Icons.explore_outlined,
    'Ruota il Knowledge Core e osserva i nodi dimostrativi.',
  );

  const JackSection(this.title, this.icon, this.description);

  final String title;
  final IconData icon;
  final String description;
}
