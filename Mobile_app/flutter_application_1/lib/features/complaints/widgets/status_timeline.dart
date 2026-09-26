import 'package:flutter/material.dart';
import '../models/complaint_status.dart';
import '../models/complaint_model.dart';

class StatusTimeline extends StatelessWidget {
  final ComplaintModel complaint;

  const StatusTimeline({super.key, required this.complaint});

  @override
  Widget build(BuildContext context) {
    final currentIndex = complaint.status.stepIndex;
    final events = {for (var e in complaint.statusHistory) e.status: e.date};

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: List.generate(ComplaintStatus.values.length, (index) {
        final status = ComplaintStatus.values[index];
        final isDone = index <= currentIndex;
        final isCurrent = index == currentIndex;
        final isLast = index == ComplaintStatus.values.length - 1;
        final eventDate = events[status];

        return IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Column(
                children: [
                  Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: isDone ? status.color : Colors.grey.shade300,
                      border: isCurrent
                          ? Border.all(color: status.color, width: 3)
                          : null,
                    ),
                    child: Icon(
                      status.icon,
                      size: 18,
                      color: isDone ? Colors.white : Colors.grey.shade600,
                    ),
                  ),
                  if (!isLast)
                    Expanded(
                      child: Container(
                        width: 3,
                        color: index < currentIndex
                            ? status.color
                            : Colors.grey.shade300,
                      ),
                    ),
                ],
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(bottom: 24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        status.label,
                        style: TextStyle(
                          fontWeight: isCurrent ? FontWeight.bold : FontWeight.w500,
                          fontSize: 15,
                          color: isDone ? Colors.black87 : Colors.grey.shade500,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        status.description,
                        style: TextStyle(
                          fontSize: 12,
                          color: isDone ? Colors.black54 : Colors.grey.shade400,
                        ),
                      ),
                      if (eventDate != null) ...[
                        const SizedBox(height: 4),
                        Text(
                          '${eventDate.day.toString().padLeft(2, '0')}/'
                          '${eventDate.month.toString().padLeft(2, '0')} à '
                          '${eventDate.hour.toString().padLeft(2, '0')}:'
                          '${eventDate.minute.toString().padLeft(2, '0')}',
                          style: TextStyle(fontSize: 11, color: Colors.grey.shade500),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      }),
    );
  }
}