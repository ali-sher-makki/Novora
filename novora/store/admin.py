from django.contrib import admin
from .models import Category, Product, UserProfile, Cart, CartItem, Wishlist, Order, OrderItem, Review

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category_type', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'stock_quantity', 'is_featured']
    list_editable = ['price', 'stock_quantity', 'is_featured']
    prepopulated_fields = {'slug': ('name',)}
    list_filter = ['category', 'is_featured']
    search_fields = ['name']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'total_amount', 'status', 'created_at']
    list_editable = ['status']
    list_filter = ['status']

admin.site.register(UserProfile)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Wishlist)
admin.site.register(OrderItem)
admin.site.register(Review)