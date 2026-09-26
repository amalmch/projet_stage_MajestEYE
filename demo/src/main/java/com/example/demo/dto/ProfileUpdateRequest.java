package com.example.demo.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class ProfileUpdateRequest {
    @NotBlank(message = "Full name is required")
    private String fullName;
    private String phone;
    private String address;
    private String governorate;
    private String delegation;
}
