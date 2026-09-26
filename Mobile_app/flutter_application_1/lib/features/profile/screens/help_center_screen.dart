import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../core/theme/app_theme.dart';

class HelpCenterScreen extends StatelessWidget {
  const HelpCenterScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: AppBar(title: const Text('Centre d\'aide')),
      body: ListView(
        padding: const EdgeInsets.all(16.0),
        children: [
          _buildFaqItem(
            context,
            'Comment soumettre une réclamation ?',
            'Allez dans l\'onglet Assistant et décrivez votre problème. L\'assistant créera automatiquement une réclamation pour vous.',
          ),
          const SizedBox(height: 12),
          _buildFaqItem(
            context,
            'Comment suivre ma réclamation ?',
            'Allez dans l\'onglet Réclamations pour voir la liste de toutes vos réclamations et leur statut en temps réel.',
          ),
          const SizedBox(height: 12),
          _buildFaqItem(
            context,
            'Comment changer la langue ?',
            'Allez dans Mon profil > Paramètres > Langue de l\'application et choisissez Français ou Arabe.',
          ),
        ],
      ),
    );
  }

  Widget _buildFaqItem(BuildContext context, String question, String answer) {
    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(AppTheme.radiusMd),
        boxShadow: AppTheme.softShadow,
      ),
      child: ExpansionTile(
        title: Text(
          question,
          style: GoogleFonts.poppins(
            fontWeight: FontWeight.w600,
            fontSize: 14,
            color: Theme.of(context).textTheme.bodyLarge?.color,
          ),
        ),
        childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        children: [
          Text(
            answer,
            style: GoogleFonts.inter(
              fontSize: 14,
              color: Theme.of(context).textTheme.bodyMedium?.color,
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }
}
