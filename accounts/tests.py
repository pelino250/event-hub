from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

User = get_user_model()


class CustomUserModelTest(TestCase):
    """Test the custom user model"""
    
    def test_create_user_with_email(self):
        """Test creating a user with email"""
        email = 'test@example.com'
        password = 'testpass123'
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name='Test',
            last_name='User'
        )
        
        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        
    def test_create_superuser(self):
        """Test creating a superuser"""
        email = 'admin@example.com'
        password = 'adminpass123'
        user = User.objects.create_superuser(
            email=email,
            password=password
        )
        
        self.assertEqual(user.email, email)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        
    def test_user_string_representation(self):
        """Test the string representation of user"""
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.assertEqual(str(user), 'test@example.com')


class AccountsAPITest(APITestCase):
    """Test accounts functionality"""
    
    def test_user_model_exists(self):
        """Test that user model is properly configured"""
        self.assertTrue(hasattr(User, 'email'))
        self.assertTrue(hasattr(User, 'first_name'))
        self.assertTrue(hasattr(User, 'last_name'))