package com.example.demo.dto;

import com.example.demo.model.Role;
import com.example.demo.model.User;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class UserDTO {
    private String id;
    private String fullName;
    private String email;
    private Role role;
    private String phone;
    private String address;
    private String governorate;
    private String delegation;
    private String profileImageBase64;
    private LocalDateTime createdAt;

    public static UserDTO fromUser(User user) {
        if (user == null) return null;
        return UserDTO.builder()
                .id(user.getId())
                .fullName(user.getFullName())
                .email(user.getEmail())
                .role(user.getRole())
                .phone(user.getPhone())
                .address(user.getAddress())
                .governorate(user.getGovernorate())
                .delegation(user.getDelegation())
                .profileImageBase64(user.getProfileImageBase64())
                .createdAt(user.getCreatedAt())
                .build();
    }
}
