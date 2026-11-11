import 'package:flutter/material.dart';

class ModulesScreen extends StatefulWidget {
  const ModulesScreen({super.key});
  @override
  State<ModulesScreen> createState() => _ModulesScreenState;
}

class _ModulesScreenState extends State<ModulesScreen> {
  @override
  Widget build(BuildContext context) => const Scaffold(
    body: Center(child: Text('Moduli M2'))
  );
