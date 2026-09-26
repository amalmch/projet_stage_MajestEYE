package com.example.demo.controller;

import com.example.demo.dto.ChangePasswordRequest;
import com.example.demo.dto.UpdateProfileRequest;
import com.example.demo.dto.UserDTO;
import com.example.demo.service.UserService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    // --- Citizen Endpoints ---

    @GetMapping("/users/me")
    public ResponseEntity<UserDTO> getMyProfile(Authentication authentication) {
        return ResponseEntity.ok(userService.getProfile(authentication.getName()));
    }

    @PutMapping("/users/me")
    public ResponseEntity<UserDTO> updateMyProfile(
            Authentication authentication,
            @RequestBody UpdateProfileRequest request
    ) {
        return ResponseEntity.ok(userService.updateProfile(authentication.getName(), request));
    }

    @PutMapping("/users/me/password")
    public ResponseEntity<Map<String, String>> changeMyPassword(
            Authentication authentication,
            @Valid @RequestBody ChangePasswordRequest request
    ) {
        userService.changePassword(authentication.getName(), request);
        return ResponseEntity.ok(Map.of("message", "Password changed successfully"));
    }

    // --- Admin Endpoints ---

    @PostMapping("/admin/users")
    public ResponseEntity<UserDTO> createStaffUser(@Valid @RequestBody com.example.demo.dto.CreateStaffRequest request) {
        return ResponseEntity.ok(userService.createStaffUser(request));
    }

    @GetMapping("/admin/users/all")
    public ResponseEntity<List<UserDTO>> getAllUsers() {
        return ResponseEntity.ok(userService.getAllUsers());
    }

    @GetMapping("/admin/technicians")
    public ResponseEntity<List<UserDTO>> getAllTechnicians() {
        return ResponseEntity.ok(userService.getAllTechnicians());
    }

    @GetMapping("/admin/users")
    public ResponseEntity<List<UserDTO>> getAllCitizens() {
        return ResponseEntity.ok(userService.getAllCitizens());
    }

    @DeleteMapping("/admin/users/{id}")
    public ResponseEntity<Map<String, String>> deleteUser(@PathVariable String id) {
        userService.deleteUser(id);
        return ResponseEntity.ok(Map.of("message", "User deleted successfully"));
    }
}
