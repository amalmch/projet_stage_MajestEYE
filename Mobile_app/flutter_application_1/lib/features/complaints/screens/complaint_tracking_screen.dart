import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/complaint_provider.dart';
import '../../auth/providers/auth_provider.dart';
import '../models/complaint_category.dart';
import '../models/complaint_status.dart';
import 'complaint_detail_screen.dart';

class ComplaintTrackingScreen extends StatefulWidget {
  const ComplaintTrackingScreen({super.key});

  @override
  State<ComplaintTrackingScreen> createState() => _ComplaintTrackingScreenState();
}

class _ComplaintTrackingScreenState extends State<ComplaintTrackingScreen> {
  String? _lastFetchedEmail;

  @override
  void initState() {
    super.initState();
    _fetch();
  }

  void _fetch() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final email = context.read<AuthProvider>().userEmail;
      if (email != null && email.isNotEmpty) {
        _lastFetchedEmail = email;
        context.read<ComplaintProvider>().fetchUserComplaints(email);
      }
    });
  }

  String _categoryLabel(String code) {
    final match = complaintCategories.where((c) => c.code == code);
    return match.isNotEmpty ? match.first.label : code;
  }

  @override
  Widget build(BuildContext context) {
    final currentEmail = context.watch<AuthProvider>().userEmail;
    if (currentEmail != null && currentEmail.isNotEmpty && currentEmail != _lastFetchedEmail) {
      _lastFetchedEmail = currentEmail;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        context.read<ComplaintProvider>().fetchUserComplaints(currentEmail);
      });
    }

    final complaintProvider = context.watch<ComplaintProvider>();
    final complaints = complaintProvider.complaints;
    final isLoading = complaintProvider.isLoading;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Mes réclamations'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              if (currentEmail != null && currentEmail.isNotEmpty) {
                context.read<ComplaintProvider>().fetchUserComplaints(currentEmail);
              }
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          if (currentEmail != null && currentEmail.isNotEmpty) {
            await context.read<ComplaintProvider>().fetchUserComplaints(currentEmail);
          }
        },
        child: isLoading 
            ? const Center(child: CircularProgressIndicator())
            : complaints.isEmpty
                ? ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    children: [
                      SizedBox(
                        height: MediaQuery.of(context).size.height * 0.6,
                        child: Center(
                          child: Padding(
                            padding: const EdgeInsets.all(24),
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(Icons.inbox_outlined, size: 56, color: Colors.grey.shade400),
                                const SizedBox(height: 12),
                                Text(
                                  'Aucune réclamation pour le moment.',
                                  style: TextStyle(color: Colors.grey.shade600),
                                  textAlign: TextAlign.center,
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ],
                  )
                : ListView.separated(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(16),
                    itemCount: complaints.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 10),
                    itemBuilder: (context, index) {
                      final complaint = complaints[index];
                      return Card(
                        elevation: 0,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                          side: BorderSide(color: Colors.grey.shade200),
                        ),
                        child: ListTile(
                          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                          leading: CircleAvatar(
                            backgroundColor: complaint.status.color.withOpacity(0.15),
                            child: Icon(complaint.status.icon, color: complaint.status.color),
                          ),
                          title: Text(
                            _categoryLabel(complaint.categorie),
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                          subtitle: Text(
                            complaint.texte,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          trailing: Chip(
                            label: Text(
                              complaint.status.label,
                              style: const TextStyle(fontSize: 11, color: Colors.white),
                            ),
                            backgroundColor: complaint.status.color,
                            padding: EdgeInsets.zero,
                            materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                          ),
                          onTap: () {
                            Navigator.of(context).push(
                              MaterialPageRoute(
                                builder: (_) => ComplaintDetailScreen(complaintId: complaint.id),
                              ),
                            );
                          },
                        ),
                      );
                    },
                  ),
      ),
    );
  }
}