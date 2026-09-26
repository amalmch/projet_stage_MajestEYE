import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:flutter_application_1/l10n/app_localizations.dart';

import '../../../core/theme/app_theme.dart';
import '../../../core/theme/theme_provider.dart';
import '../providers/locale_provider.dart';

import '../../profile/screens/about_screen.dart';
import '../../profile/screens/privacy_screen.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final localeProvider = context.watch<LocaleProvider>();
    final themeProvider = context.watch<ThemeProvider>();
    final isDark = themeProvider.isDarkMode;
    final cardColor = Theme.of(context).cardColor;
    final l10n = AppLocalizations.of(context)!;

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: AppBar(
        title: Text(l10n.settings),
      ),
      body: ListView(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
        children: [
          // ── Apparence ──
          Text(
            l10n.appearance,
            style: GoogleFonts.poppins(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: AppTheme.primary,
            ),
          ),
          const SizedBox(height: 12),
          _SettingsCard(
            color: cardColor,
            children: [
              ListTile(
                leading: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: isDark ? Colors.blue.withOpacity(0.2) : Colors.blue.shade50,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(Icons.dark_mode_outlined, color: Colors.blue),
                ),
                title: Text(
                  l10n.darkMode,
                  style: GoogleFonts.inter(
                    fontWeight: FontWeight.w500,
                    color: Theme.of(context).textTheme.bodyLarge?.color,
                  ),
                ),
                trailing: Switch(
                  value: themeProvider.isDarkMode,
                  onChanged: (val) {
                    themeProvider.toggleTheme(val);
                  },
                  activeColor: AppTheme.primary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // ── Langue ──
          Text(
            l10n.appLanguage,
            style: GoogleFonts.poppins(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: AppTheme.primary,
            ),
          ),
          const SizedBox(height: 12),
          _SettingsCard(
            color: cardColor,
            children: [
              RadioListTile<String>(
                title: Text(l10n.french, style: GoogleFonts.inter(fontWeight: FontWeight.w500)),
                value: 'fr',
                groupValue: localeProvider.locale.languageCode,
                activeColor: AppTheme.primary,
                onChanged: (value) {
                  context.read<LocaleProvider>().setLocale(const Locale('fr'));
                },
              ),
              const Divider(height: 1, indent: 16, endIndent: 16),
              RadioListTile<String>(
                title: Text(l10n.arabic, style: GoogleFonts.inter(fontWeight: FontWeight.w500)),
                value: 'ar',
                groupValue: localeProvider.locale.languageCode,
                activeColor: AppTheme.primary,
                onChanged: (value) {
                  context.read<LocaleProvider>().setLocale(const Locale('ar'));
                },
              ),
            ],
          ),
          const SizedBox(height: 24),

          // ── Informations ──
          Text(
            l10n.information,
            style: GoogleFonts.poppins(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: AppTheme.primary,
            ),
          ),
          const SizedBox(height: 12),
          _SettingsCard(
            color: cardColor,
            children: [
              ListTile(
                leading: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.purple.shade50,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(Icons.info_outline_rounded, color: Colors.purple),
                ),
                title: Text(l10n.aboutSonede, style: GoogleFonts.inter(fontWeight: FontWeight.w500)),
                trailing: const Icon(Icons.chevron_right_rounded, color: Colors.grey),
                onTap: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const AboutScreen()),
                  );
                },
              ),
              const Divider(height: 1, indent: 56),
              ListTile(
                leading: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Colors.orange.shade50,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Icon(Icons.security_outlined, color: Colors.orange),
                ),
                title: Text(l10n.privacy, style: GoogleFonts.inter(fontWeight: FontWeight.w500)),
                trailing: const Icon(Icons.chevron_right_rounded, color: Colors.grey),
                onTap: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const PrivacyScreen()),
                  );
                },
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SettingsCard extends StatelessWidget {
  final List<Widget> children;
  final Color? color;

  const _SettingsCard({required this.children, this.color});

  @override
  Widget build(BuildContext context) {
    return Material(
      color: color ?? Theme.of(context).cardColor,
      borderRadius: BorderRadius.circular(AppTheme.radiusMd),
      elevation: 0,
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(AppTheme.radiusMd),
          boxShadow: AppTheme.softShadow,
        ),
        child: Column(
          children: children,
        ),
      ),
    );
  }
}