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
    'Crea e cerca ricordi inseriti da te, salvati localmente su questo Mac.',
  ),
  planning(
    'Pianificazione',
    Icons.route_outlined,
    'Attività e promemoria sono anteprime non collegate.',
  ),
  modules(
    'Moduli',
    Icons.widgets_outlined,
    'Gestisci modelli e routing demo senza inviare richieste AI.',
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
