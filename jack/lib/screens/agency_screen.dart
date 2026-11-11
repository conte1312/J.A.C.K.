import 'package:flutter/material.dart';

/// Agency — catalogo agenti upstream (preview M2).
/// Dati provenienti dal catalogo Msitarzewski/agency-agents: 272 profili,
/// 20 divisioni. Funzionalità complete pianificate in M6-M7.
class AgencyScreen extends StatefulWidget {
  const AgencyScreen({super.key});
  @override
  State<AgencyScreen> createState() => _AgencyScreenState;
}

class _AgencyScreenState extends State<AgencyScreen> {
  @override
  Widget build(BuildContext context) => const Scaffold(
    body: Center(child: Text('Agency M2 - Preview catalog upstream'))
  );
