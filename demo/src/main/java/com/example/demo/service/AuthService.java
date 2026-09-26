package com.example.demo.service;

import com.example.demo.dto.AuthRequest;
import com.example.demo.dto.AuthResponse;
import com.example.demo.dto.RegisterRequest;
import com.example.demo.dto.UserDTO;
import com.example.demo.exception.ApiException;
import com.example.demo.model.User;
import com.example.demo.repository.UserRepository;
import com.example.demo.security.JwtService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;
    private final AuthenticationManager authenticationManager;
    private final EmailService emailService;

    public java.util.List<User> getDebugUsers() {
        return userRepository.findAll();
    }

    private String generateRandomCode() {
        return String.format("%06d", new java.util.Random().nextInt(999999));
    }

    public AuthResponse register(RegisterRequest request) {
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new ApiException("Email is already in use", HttpStatus.BAD_REQUEST);
        }

        User user = User.builder()
                .fullName(request.getFullName())
                .email(request.getEmail())
                .password(passwordEncoder.encode(request.getPassword()))
                .phone(request.getPhone())
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .enabled(false)
                .verificationCode(generateRandomCode())
                .verificationCodeExpiresAt(LocalDateTime.now().plusMinutes(15))
                .build();

        user = userRepository.save(user);

        // Send email
        emailService.sendVerificationEmail(user.getEmail(), user.getFullName(), user.getVerificationCode());

        return AuthResponse.builder()
                .token(null) // Do not return token until verified
                .refreshToken(null)
                .user(UserDTO.fromUser(user))
                .build();
    }

    public AuthResponse login(AuthRequest request) {
        authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(
                        request.getEmail(),
                        request.getPassword()
                )
        );

        User user = userRepository.findByEmail(request.getEmail())
                .orElseThrow(() -> new ApiException("User not found", HttpStatus.NOT_FOUND));

        if (!user.isEnabled()) {
            throw new ApiException("Veuillez vérifier votre adresse email avant de vous connecter.", HttpStatus.FORBIDDEN);
        }

        String jwtToken = jwtService.generateAccessToken(user);
        String refreshToken = jwtService.generateRefreshToken(user);

        return AuthResponse.builder()
                .token(jwtToken)
                .refreshToken(refreshToken)
                .user(UserDTO.fromUser(user))
                .build();
    }

    public AuthResponse verifyEmail(String email, String code) {
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new ApiException("User not found", HttpStatus.NOT_FOUND));

        if (user.isEnabled()) {
            throw new ApiException("User is already verified", HttpStatus.BAD_REQUEST);
        }

        if (user.getVerificationCode() == null || !user.getVerificationCode().equals(code)) {
            throw new ApiException("Invalid verification code", HttpStatus.BAD_REQUEST);
        }

        if (user.getVerificationCodeExpiresAt() != null && user.getVerificationCodeExpiresAt().isBefore(LocalDateTime.now())) {
            throw new ApiException("Verification code expired", HttpStatus.BAD_REQUEST);
        }

        user.setEnabled(true);
        user.setVerificationCode(null);
        user.setVerificationCodeExpiresAt(null);
        userRepository.save(user);

        String jwtToken = jwtService.generateAccessToken(user);
        String refreshToken = jwtService.generateRefreshToken(user);

        return AuthResponse.builder()
                .token(jwtToken)
                .refreshToken(refreshToken)
                .user(UserDTO.fromUser(user))
                .build();
    }

    public void forgotPassword(String email) {
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new ApiException("User not found", HttpStatus.NOT_FOUND));

        String code = generateRandomCode();
        user.setResetPasswordToken(code);
        user.setResetPasswordTokenExpiresAt(LocalDateTime.now().plusMinutes(15));
        userRepository.save(user);

        emailService.sendPasswordResetEmail(user.getEmail(), user.getFullName(), code);
    }

    public void resetPassword(String email, String code, String newPassword) {
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new ApiException("User not found", HttpStatus.NOT_FOUND));

        if (user.getResetPasswordToken() == null || !user.getResetPasswordToken().equals(code)) {
            throw new ApiException("Invalid reset code", HttpStatus.BAD_REQUEST);
        }

        if (user.getResetPasswordTokenExpiresAt() != null && user.getResetPasswordTokenExpiresAt().isBefore(LocalDateTime.now())) {
            throw new ApiException("Reset code expired", HttpStatus.BAD_REQUEST);
        }

        user.setPassword(passwordEncoder.encode(newPassword));
        user.setResetPasswordToken(null);
        user.setResetPasswordTokenExpiresAt(null);
        userRepository.save(user);
    }
}
