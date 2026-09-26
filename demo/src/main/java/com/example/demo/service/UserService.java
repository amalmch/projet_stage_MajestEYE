package com.example.demo.service;

import com.example.demo.dto.ChangePasswordRequest;
import com.example.demo.dto.UpdateProfileRequest;
import com.example.demo.dto.UserDTO;
import com.example.demo.exception.ApiException;
import com.example.demo.model.Role;
import com.example.demo.model.User;
import com.example.demo.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class UserService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    public UserDTO getProfile(String email) {
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new ApiException("User not found", HttpStatus.NOT_FOUND));
        return UserDTO.fromUser(user);
    }

    public UserDTO updateProfile(String email, UpdateProfileRequest request) {
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new ApiException("User not found", HttpStatus.NOT_FOUND));

        if (request.getFullName() != null) user.setFullName(request.getFullName());
        if (request.getPhone() != null) user.setPhone(request.getPhone());
        if (request.getAddress() != null) user.setAddress(request.getAddress());
        if (request.getGovernorate() != null) user.setGovernorate(request.getGovernorate());
        if (request.getDelegation() != null) user.setDelegation(request.getDelegation());
        
        user.setUpdatedAt(LocalDateTime.now());

        user = userRepository.save(user);
        return UserDTO.fromUser(user);
    }

    public void changePassword(String email, ChangePasswordRequest request) {
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new ApiException("User not found", HttpStatus.NOT_FOUND));

        if (!passwordEncoder.matches(request.getCurrentPassword(), user.getPassword())) {
            throw new ApiException("Wrong current password", HttpStatus.BAD_REQUEST);
        }

        user.setPassword(passwordEncoder.encode(request.getNewPassword()));
        user.setUpdatedAt(LocalDateTime.now());
        userRepository.save(user);
    }

    // Admin methods
    public UserDTO createStaffUser(com.example.demo.dto.CreateStaffRequest request) {
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new ApiException("Email is already in use", HttpStatus.BAD_REQUEST);
        }

        User user = User.builder()
                .fullName(request.getFullName())
                .email(request.getEmail())
                .password(passwordEncoder.encode(request.getPassword()))
                .role(request.getRole())
                .phone(request.getPhone())
                .address(request.getAddress())
                .governorate(request.getGovernorate())
                .delegation(request.getDelegation())
                .enabled(true)
                .createdAt(LocalDateTime.now())
                .updatedAt(LocalDateTime.now())
                .build();

        user = userRepository.save(user);
        return UserDTO.fromUser(user);
    }

    public List<UserDTO> getAllUsers() {
        return userRepository.findAll().stream()
                .map(UserDTO::fromUser)
                .collect(Collectors.toList());
    }

    public List<UserDTO> getAllTechnicians() {
        return userRepository.findByRole(Role.TECHNICIEN).stream()
                .map(UserDTO::fromUser)
                .collect(Collectors.toList());
    }

    public List<UserDTO> getAllCitizens() {
        return userRepository.findByRole(Role.CITIZEN).stream()
                .map(UserDTO::fromUser)
                .collect(Collectors.toList());
    }

    public void deleteUser(String id) {
        if (!userRepository.existsById(id)) {
            throw new ApiException("User not found", HttpStatus.NOT_FOUND);
        }
        userRepository.deleteById(id);
    }
}
