import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../core/theme/app_theme.dart';
import '../../auth/screens/login_screen.dart';

class WelcomeScreen extends StatefulWidget {
  const WelcomeScreen({super.key});

  @override
  State<WelcomeScreen> createState() => _WelcomeScreenState();
}

class _WelcomeScreenState extends State<WelcomeScreen>
    with TickerProviderStateMixin {
  final _pageController = PageController();
  int _currentPage = 0;

  late final AnimationController _fadeController;
  late final Animation<double> _fadeAnimation;
  late final AnimationController _pulseController;

  static const _pages = [
    _PageData(
      icon: Icons.water_drop_rounded,
      title: 'Bienvenue à SONEDE',
      subtitle:
          'Votre partenaire de confiance pour l\'eau potable en Tunisie.\n'
          'Au service du citoyen, 24h/24.',
      gradient: [Color(0xFF0D2B45), Color(0xFF1F4E78)],
    ),
    _PageData(
      icon: Icons.report_problem_rounded,
      title: 'Signalez un problème',
      subtitle:
          'Coupure d\'eau, fuite, qualité... Signalez votre problème en '
          'quelques secondes avec photo et localisation GPS.',
      gradient: [Color(0xFF1F4E78), Color(0xFF3A7CA5)],
    ),
    _PageData(
      icon: Icons.smart_toy_rounded,
      title: 'Assistant intelligent',
      subtitle:
          'Notre assistant IA comprend le Tunisien, le Français et l\'Arabe.\n'
          'Posez vos questions à tout moment !',
      gradient: [Color(0xFF3A7CA5), Color(0xFF5CB8E4)],
    ),
  ];

  @override
  void initState() {
    super.initState();
    _fadeController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );
    _fadeAnimation = CurvedAnimation(
      parent: _fadeController,
      curve: Curves.easeOut,
    );
    _fadeController.forward();

    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pageController.dispose();
    _fadeController.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  Future<void> _onGetStarted() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('onboarding_seen', true);
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          // Page content
          PageView.builder(
            controller: _pageController,
            itemCount: _pages.length,
            onPageChanged: (i) => setState(() => _currentPage = i),
            itemBuilder: (context, index) {
              final page = _pages[index];
              return _buildPage(page);
            },
          ),
          // Bottom controls
          Positioned(
            left: 0,
            right: 0,
            bottom: 0,
            child: SafeArea(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // Page dots
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: List.generate(
                        _pages.length,
                        (i) => AnimatedContainer(
                          duration: const Duration(milliseconds: 300),
                          margin: const EdgeInsets.symmetric(horizontal: 4),
                          width: _currentPage == i ? 28 : 8,
                          height: 8,
                          decoration: BoxDecoration(
                            color: _currentPage == i
                                ? Colors.white
                                : Colors.white.withOpacity(0.4),
                            borderRadius: BorderRadius.circular(4),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 32),
                    // Button
                    if (_currentPage == _pages.length - 1)
                      FadeTransition(
                        opacity: _fadeAnimation,
                        child: SizedBox(
                          width: double.infinity,
                          height: 56,
                          child: ElevatedButton(
                            onPressed: _onGetStarted,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.white,
                              foregroundColor: AppTheme.primary,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(AppTheme.radiusLg),
                              ),
                              elevation: 4,
                            ),
                            child: Text(
                              'Commencer',
                              style: GoogleFonts.poppins(
                                fontSize: 17,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ),
                      )
                    else
                      SizedBox(
                        width: double.infinity,
                        height: 56,
                        child: OutlinedButton(
                          onPressed: () {
                            _pageController.nextPage(
                              duration: const Duration(milliseconds: 400),
                              curve: Curves.easeInOut,
                            );
                          },
                          style: OutlinedButton.styleFrom(
                            foregroundColor: Colors.white,
                            side: const BorderSide(color: Colors.white54, width: 1.5),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(AppTheme.radiusLg),
                            ),
                          ),
                          child: Text(
                            'Suivant',
                            style: GoogleFonts.poppins(
                              fontSize: 17,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ),
                      ),
                    const SizedBox(height: 8),
                    if (_currentPage < _pages.length - 1)
                      TextButton(
                        onPressed: _onGetStarted,
                        child: Text(
                          'Passer',
                          style: GoogleFonts.inter(
                            color: Colors.white70,
                            fontSize: 14,
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPage(_PageData page) {
    return AnimatedBuilder(
      animation: _pulseController,
      builder: (context, child) {
        final pulse = 1.0 + (_pulseController.value * 0.03);
        return Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: page.gradient,
            ),
          ),
          child: SafeArea(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Spacer(flex: 2),
                  // Animated icon
                  Transform.scale(
                    scale: pulse,
                    child: Container(
                      width: 120,
                      height: 120,
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.15),
                        shape: BoxShape.circle,
                      ),
                      child: Icon(
                        page.icon,
                        size: 56,
                        color: Colors.white,
                      ),
                    ),
                  ),
                  const SizedBox(height: 48),
                  Text(
                    page.title,
                    textAlign: TextAlign.center,
                    style: GoogleFonts.poppins(
                      fontSize: 28,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                      height: 1.2,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    page.subtitle,
                    textAlign: TextAlign.center,
                    style: GoogleFonts.inter(
                      fontSize: 15,
                      color: Colors.white.withOpacity(0.85),
                      height: 1.5,
                    ),
                  ),
                  const Spacer(flex: 3),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _PageData {
  final IconData icon;
  final String title;
  final String subtitle;
  final List<Color> gradient;

  const _PageData({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.gradient,
  });
}
