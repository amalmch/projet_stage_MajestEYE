package com.example.demo.config;

import com.example.demo.model.Role;
import com.example.demo.model.User;
import com.example.demo.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;

@Component
@RequiredArgsConstructor
@Slf4j
public class DataInitializer implements CommandLineRunner {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    @Override
    public void run(String... args) {
        // Initialize Admin
        initOrUpdateUser(
                "Directeur SONEDE",
                "admin@sonede.tn",
                "admin2026",
                Role.ADMIN,
                "Tunis",
                "Centre Ville",
                "+216 71 100 200"
        );

        // Initialize Technicians
        initOrUpdateUser(
                "Mohamed Ben Ali",
                "tech.tunis@sonede.tn",
                "sonede2026",
                Role.TECHNICIEN,
                "Tunis",
                "El Menzah",
                "+216 71 234 567"
        );

        initOrUpdateUser(
                "Ahmed Trabelsi",
                "tech.jendouba@sonede.tn",
                "sonede2026",
                Role.TECHNICIEN,
                "Jendouba",
                "El Hedi Ben Hassine",
                "+216 78 345 678"
        );

        initOrUpdateUser(
                "Sami Mejri",
                "tech.beja@sonede.tn",
                "sonede2026",
                Role.TECHNICIEN,
                "Béja",
                "Béja Nord",
                "+216 78 456 789"
        );
    }

    private void initOrUpdateUser(
            String fullName,
            String email,
            String password,
            Role role,
            String governorate,
            String delegation,
            String phone
    ) {
        User user = userRepository.findByEmail(email).orElse(null);
        if (user == null) {
            user = User.builder()
                    .fullName(fullName)
                    .email(email)
                    .password(passwordEncoder.encode(password))
                    .role(role)
                    .phone(phone)
                    .address("Bureau SONEDE " + governorate)
                    .governorate(governorate)
                    .delegation(delegation)
                    .enabled(true)
                    .createdAt(LocalDateTime.now())
                    .updatedAt(LocalDateTime.now())
                    .build();
            userRepository.save(user);
            log.info("Created user account via Spring Boot: {} [{}]", email, role);
        } else {
            // Update password & enable
            user.setPassword(passwordEncoder.encode(password));
            user.setEnabled(true);
            user.setRole(role);
            user.setGovernorate(governorate);
            user.setDelegation(delegation);
            user.setUpdatedAt(LocalDateTime.now());
            userRepository.save(user);
            log.info("Updated existing user account via Spring Boot: {} [{}]", email, role);
        }
    }
}
