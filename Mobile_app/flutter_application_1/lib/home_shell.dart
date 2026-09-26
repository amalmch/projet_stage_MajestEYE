import 'package:flutter/material.dart';
import 'features/chatbot/screens/chatbot_screen.dart';
import 'features/complaints/screens/complaint_tracking_screen.dart';
import 'features/profile/screens/profile_screen.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _currentIndex = 0;

  static const _screens = [
    ChatbotScreen(),
    ComplaintTrackingScreen(),
    ProfileScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: _screens,
      ),
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.05),
              blurRadius: 10,
              offset: const Offset(0, -5),
            ),
          ],
        ),
        child: NavigationBar(
          selectedIndex: _currentIndex,
          onDestinationSelected: (index) {
            setState(() => _currentIndex = index);
          },
          destinations: [
            NavigationDestination(
              icon: const Icon(Icons.chat_bubble_outline),
              selectedIcon: const Icon(Icons.chat_bubble_rounded),
              label: 'Chatbot',
            ),
            NavigationDestination(
              icon: const Icon(Icons.format_list_bulleted_outlined),
              selectedIcon: const Icon(Icons.format_list_bulleted_rounded),
              label: 'Réclamations',
            ),
            NavigationDestination(
              icon: const Icon(Icons.person_outline),
              selectedIcon: const Icon(Icons.person_rounded),
              label: 'Profil',
            ),
          ],
        ),
      ),
    );
  }
}
