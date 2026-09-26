package com.example.demo.controller;

import com.example.demo.dto.ProfileImageRequest;
import com.example.demo.dto.ProfileUpdateRequest;
import com.example.demo.dto.UserDTO;
import com.example.demo.model.User;
import com.example.demo.repository.UserRepository;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;

@RestController
@RequestMapping("/api/profile")
@RequiredArgsConstructor
public class ProfileController {

    private final UserRepository userRepository;

    @GetMapping
    public ResponseEntity<UserDTO> getProfile(Authentication authentication) {
        User user = userRepository.findByEmail(authentication.getName())
                .orElseThrow(() -> new RuntimeException("User not found"));
        return ResponseEntity.ok(UserDTO.fromUser(user));
    }

    @PutMapping
    public ResponseEntity<UserDTO> updateProfile(
            @Valid @RequestBody ProfileUpdateRequest request,
            Authentication authentication) {
        
        User user = userRepository.findByEmail(authentication.getName())
                .orElseThrow(() -> new RuntimeException("User not found"));

        user.setFullName(request.getFullName());
        user.setPhone(request.getPhone());
        user.setAddress(request.getAddress());
        user.setGovernorate(request.getGovernorate());
        user.setDelegation(request.getDelegation());
        user.setUpdatedAt(LocalDateTime.now());

        User updatedUser = userRepository.save(user);
        return ResponseEntity.ok(UserDTO.fromUser(updatedUser));
    }

    @PostMapping("/image")
    public ResponseEntity<UserDTO> uploadProfileImage(
            @RequestBody ProfileImageRequest request,
            Authentication authentication) {
        
        User user = userRepository.findByEmail(authentication.getName())
                .orElseThrow(() -> new RuntimeException("User not found"));

        user.setProfileImageBase64(request.getImageBase64());
        user.setUpdatedAt(LocalDateTime.now());

        User updatedUser = userRepository.save(user);
        return ResponseEntity.ok(UserDTO.fromUser(updatedUser));
    }
}
