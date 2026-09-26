import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class PrivacyScreen extends StatelessWidget {
  const PrivacyScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: AppBar(title: const Text('Confidentialité')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Politique de confidentialité',
              style: GoogleFonts.poppins(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: Theme.of(context).textTheme.bodyLarge?.color,
              ),
            ),
            const SizedBox(height: 16),
            Text(
              '1. Collecte des données\n'
              'Nous collectons les données nécessaires pour gérer votre profil et traiter vos réclamations. Cela inclut votre nom, email, téléphone et adresse.\n\n'
              '2. Utilisation des données\n'
              'Vos données sont utilisées exclusivement pour vous fournir le service de gestion des abonnements et des réclamations liées à la SONEDE.\n\n'
              '3. Protection des données\n'
              'Nous mettons en œuvre des mesures de sécurité pour protéger vos informations personnelles contre l\'accès non autorisé.\n\n'
              '4. Partage des données\n'
              'Vos informations ne sont pas partagées avec des tiers, sauf si requis par la loi tunisienne.',
              style: GoogleFonts.inter(
                fontSize: 15,
                height: 1.6,
                color: Theme.of(context).textTheme.bodyLarge?.color,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
