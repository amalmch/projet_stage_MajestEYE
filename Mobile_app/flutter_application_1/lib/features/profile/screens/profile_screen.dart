import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:image_picker/image_picker.dart';
import 'package:flutter_application_1/l10n/app_localizations.dart';

import '../../../core/theme/app_theme.dart';
import '../../auth/providers/auth_provider.dart';
import '../../auth/screens/login_screen.dart';
import '../../settings/screens/settings_screen.dart';
import 'account_screen.dart';
import 'about_screen.dart';
import 'privacy_screen.dart';
import 'help_center_screen.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final ImagePicker _picker = ImagePicker();
  bool _isUploading = false;

  Future<void> _pickAndUploadImage() async {
    try {
      final XFile? image = await _picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 800,
        imageQuality: 70,
      );
      if (image == null) return;

      setState(() => _isUploading = true);

      final bytes = await image.readAsBytes();
      final base64String = base64Encode(bytes);

      if (mounted) {
        await context.read<AuthProvider>().uploadProfileImage(base64String);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Image de profil mise à jour')), // Could translate this too
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Erreur: $e'), backgroundColor: Colors.red),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isUploading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final userName = auth.userName ?? 'Utilisateur';
    final userEmail = auth.userEmail ?? 'utilisateur@email.com';
    final initial = userName.isNotEmpty ? userName[0].toUpperCase() : '?';
    final l10n = AppLocalizations.of(context)!;

    Widget avatarContent;
    if (_isUploading) {
      avatarContent = const CircularProgressIndicator(color: AppTheme.primary);
    } else if (auth.profileImageBase64 != null && auth.profileImageBase64!.isNotEmpty) {
      avatarContent = ClipOval(
        child: Image.memory(
          base64Decode(auth.profileImageBase64!),
          width: 90,
          height: 90,
          fit: BoxFit.cover,
        ),
      );
    } else {
      avatarContent = Text(
        initial,
        style: GoogleFonts.poppins(
          fontSize: 36,
          fontWeight: FontWeight.bold,
          color: AppTheme.primary,
        ),
      );
    }

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: AppBar(
        title: Text(l10n.profile),
        elevation: 0,
        backgroundColor: Colors.transparent,
        foregroundColor: Theme.of(context).textTheme.bodyLarge?.color,
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        child: Column(
          children: [
            // ── Avatar & Info Card ──
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                gradient: AppTheme.headerGradient,
                borderRadius: BorderRadius.circular(24),
                boxShadow: [
                  BoxShadow(
                    color: AppTheme.primary.withOpacity(0.3),
                    blurRadius: 15,
                    offset: const Offset(0, 8),
                  ),
                ],
              ),
              child: Column(
                children: [
                  GestureDetector(
                    onTap: _pickAndUploadImage,
                    child: Stack(
                      children: [
                        Container(
                          width: 90,
                          height: 90,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: Colors.white,
                            border: Border.all(color: Colors.white, width: 3),
                          ),
                          child: Center(child: avatarContent),
                        ),
                        Positioned(
                          bottom: 0,
                          right: 0,
                          child: Container(
                            padding: const EdgeInsets.all(6),
                            decoration: BoxDecoration(
                              color: AppTheme.accent,
                              shape: BoxShape.circle,
                              border: Border.all(color: Colors.white, width: 2),
                            ),
                            child: const Icon(Icons.camera_alt, size: 14, color: Colors.white),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    userName,
                    style: GoogleFonts.poppins(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    userEmail,
                    style: GoogleFonts.inter(
                      fontSize: 14,
                      color: Colors.white.withOpacity(0.8),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 32),

            // ── Menu Items ──
            _ProfileMenuItem(
              icon: Icons.person_outline,
              title: l10n.myAccount,
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const AccountScreen()),
                );
              },
            ),
            const SizedBox(height: 12),
            _ProfileMenuItem(
              icon: Icons.settings_outlined,
              title: l10n.settings,
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const SettingsScreen()),
                );
              },
            ),
            const SizedBox(height: 12),
            _ProfileMenuItem(
              icon: Icons.help_outline_rounded,
              title: l10n.helpCenter,
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const HelpCenterScreen()),
                );
              },
            ),
            const SizedBox(height: 12),
            _ProfileMenuItem(
              icon: Icons.info_outline_rounded,
              title: l10n.aboutSonede,
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const AboutScreen()),
                );
              },
            ),
            const SizedBox(height: 12),
            _ProfileMenuItem(
              icon: Icons.security_outlined,
              title: l10n.privacy,
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute(builder: (_) => const PrivacyScreen()),
                );
              },
            ),
            const SizedBox(height: 24),

            // Logout Button
            Container(
              decoration: BoxDecoration(
                color: Theme.of(context).cardColor,
                borderRadius: BorderRadius.circular(AppTheme.radiusMd),
                boxShadow: AppTheme.softShadow,
              ),
              child: Material(
                color: Colors.transparent,
                child: ListTile(
                  leading: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: AppTheme.error.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.logout_rounded, color: AppTheme.error),
                  ),
                  title: Text(
                    l10n.logout,
                    style: GoogleFonts.poppins(
                      fontWeight: FontWeight.w600,
                      color: AppTheme.error,
                    ),
                  ),
                  trailing: const Icon(Icons.chevron_right_rounded, color: Colors.grey),
                  onTap: () {
                    context.read<AuthProvider>().logout();
                    Navigator.of(context).pushAndRemoveUntil(
                      MaterialPageRoute(builder: (_) => const LoginScreen()),
                      (route) => false,
                    );
                  },
                ),
              ),
            ),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }
}

class _ProfileMenuItem extends StatelessWidget {
  final IconData icon;
  final String title;
  final VoidCallback onTap;

  const _ProfileMenuItem({
    required this.icon,
    required this.title,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(AppTheme.radiusMd),
        boxShadow: AppTheme.softShadow,
      ),
      child: Material(
        color: Colors.transparent,
        child: ListTile(
          leading: Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: AppTheme.surface,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: AppTheme.primaryLight),
          ),
          title: Text(
            title,
            style: GoogleFonts.poppins(
              fontWeight: FontWeight.w500,
              color: Theme.of(context).textTheme.bodyLarge?.color ?? AppTheme.textPrimary,
            ),
          ),
          trailing: const Icon(Icons.chevron_right_rounded, color: Colors.grey),
          onTap: onTap,
        ),
      ),
    );
  }
}