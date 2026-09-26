package com.example.demo.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.index.Indexed;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Document(collection = "users")
public class User {

    @Id
    private String id;

    private String fullName;

    @Indexed(unique = true)
    private String email;

    private String password;

    @Builder.Default
    private Role role = Role.CITIZEN;

    private String phone;
    private String address;
    private String governorate;
    private String delegation;

    @Builder.Default
    private boolean enabled = false;

    private String verificationCode;
    private LocalDateTime verificationCodeExpiresAt;

    private String resetPasswordToken;
    private LocalDateTime resetPasswordTokenExpiresAt;

    private String profileImageBase64;

    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
