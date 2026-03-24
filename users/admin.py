from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.http import HttpResponse
from django.contrib import messages
import csv

from .models import User, VendorProfile, Address, Shop


# ============= CUSTOM ADMIN ACTIONS =============

def export_users_csv(modeladmin, request, queryset):
    """Export selected users to CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users_export.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Email', 'First Name', 'Last Name', 'Phone',
        'User Type', 'Is Active', 'Is Verified', 'Is Staff',
        'Date Joined', 'Last Login'
    ])
    for user in queryset:
        writer.writerow([
            user.id, user.email, user.first_name, user.last_name,
            user.phone, user.user_type, user.is_active, user.is_verified,
            user.is_staff, user.date_joined, user.last_login
        ])
    return response

export_users_csv.short_description = "Export selected users as CSV"


def mark_users_active(modeladmin, request, queryset):
    updated = queryset.update(is_active=True)
    modeladmin.message_user(request, f'{updated} users marked as active.')

mark_users_active.short_description = "Activate selected users"


def mark_users_inactive(modeladmin, request, queryset):
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f'{updated} users deactivated.')

mark_users_inactive.short_description = "Deactivate selected users"


def verify_users(modeladmin, request, queryset):
    updated = queryset.update(is_verified=True)
    modeladmin.message_user(request, f'{updated} users verified.')

verify_users.short_description = "Verify selected users"


# ============= INLINE ADMINS =============

class VendorProfileInline(admin.StackedInline):
    """Inline vendor profile inside User admin"""
    model = VendorProfile
    can_delete = False
    verbose_name = 'Vendor Profile'
    verbose_name_plural = 'Vendor Profile'
    fields = (
        'store_name', 'slug', 'description',
        'logo', 'banner',
        'business_email', 'business_phone', 'business_address',
        'business_registration_number', 'tax_id',
        'bank_name', 'account_number', 'account_holder_name',
        'is_active', 'verification_status', 'commission_rate',
    )
    readonly_fields = ('slug',)


class AddressInline(admin.TabularInline):
    """Inline addresses inside User admin"""
    model = Address
    extra = 0
    fields = (
        'address_type', 'full_name', 'phone',
        'address_line1', 'city', 'country', 'is_default'
    )
    readonly_fields = ()
    show_change_link = True


# ============= USER ADMIN =============

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    World-class User admin with full control and visibility.
    """

    # ── List view ──
    list_display = (
        'avatar_thumbnail', 'email', 'full_name_display',
        'user_type_badge', 'phone',
        'is_active_icon', 'is_verified_icon', 'is_staff_icon',
        'order_count', 'date_joined', 'last_login_display',
    )
    list_display_links = ('avatar_thumbnail', 'email', 'full_name_display')
    list_filter = (
        'user_type', 'is_active', 'is_verified',
        'is_staff', 'is_superuser', 'date_joined',
    )
    search_fields = ('email', 'first_name', 'last_name', 'phone')
    ordering = ('-date_joined',)
    date_hierarchy = 'date_joined'
    list_per_page = 30

    # ── Detail view ──
    fieldsets = (
        ('Account Credentials', {
            'fields': ('email', 'password'),
            'description': 'Core login credentials for this user account.',
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'phone'),
        }),
        ('Role & Type', {
            'fields': ('user_type',),
        }),
        ('Status & Permissions', {
            'fields': (
                'is_active', 'is_verified', 'is_staff', 'is_superuser',
                'groups', 'user_permissions',
            ),
            'classes': ('collapse',),
        }),
        ('Verification', {
            'fields': ('verification_token', 'verification_token_created'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('date_joined', 'last_login'),
            'classes': ('collapse',),
        }),
    )

    # ── Add user view ──
    add_fieldsets = (
        ('Create New User', {
            'classes': ('wide',),
            'fields': (
                'email', 'first_name', 'last_name', 'phone',
                'user_type', 'password1', 'password2',
                'is_active', 'is_staff',
            ),
        }),
    )

    readonly_fields = ('date_joined', 'last_login', 'verification_token_created')

    # Inline profiles
    inlines = [VendorProfileInline, AddressInline]

    # Actions
    actions = [
        export_users_csv,
        mark_users_active,
        mark_users_inactive,
        verify_users,
    ]

    # ── Custom display methods ──

    def avatar_thumbnail(self, obj):
        """Show profile picture or initials avatar"""
        # Since Profile model is removed, show initials only
        initials = (
            (obj.first_name[:1] + obj.last_name[:1]).upper()
            if obj.first_name or obj.last_name
            else obj.email[:2].upper()
        )
        colors = {
            'customer': '#2563eb',
            'vendor':   '#f59e0b',
            'admin':    '#ef4444',
        }
        bg = colors.get(obj.user_type, '#94a3b8')
        return format_html(
            '<div style="width:38px;height:38px;border-radius:50%;'
            'background:{};display:flex;align-items:center;'
            'justify-content:center;color:#fff;font-weight:700;'
            'font-size:0.75rem;">{}</div>',
            bg, initials
        )

    avatar_thumbnail.short_description = ''

    def full_name_display(self, obj):
        full = obj.get_full_name()
        return full if full else format_html('<span style="color:#94a3b8;">—</span>')

    full_name_display.short_description = 'Full Name'
    full_name_display.admin_order_field = 'first_name'

    def user_type_badge(self, obj):
        styles = {
            'customer': ('background:#dbeafe;color:#1d4ed8;', 'Customer'),
            'vendor':   ('background:#fef3c7;color:#b45309;', 'Vendor'),
            'admin':    ('background:#fee2e2;color:#b91c1c;', 'Admin'),
        }
        style, label = styles.get(obj.user_type, ('background:#f1f5f9;color:#475569;', obj.user_type.title()))
        return format_html(
            '<span style="{}padding:3px 10px;border-radius:50px;'
            'font-size:11px;font-weight:700;">{}</span>',
            style, label
        )

    user_type_badge.short_description = 'Type'
    user_type_badge.admin_order_field = 'user_type'

    def is_active_icon(self, obj):
        if obj.is_active:
            return format_html('<span style="color:#10b981;font-size:1.1rem;" title="Active">✔</span>')
        return format_html('<span style="color:#ef4444;font-size:1.1rem;" title="Inactive">✘</span>')

    is_active_icon.short_description = 'Active'
    is_active_icon.admin_order_field = 'is_active'

    def is_verified_icon(self, obj):
        if obj.is_verified:
            return format_html('<span style="color:#2563eb;font-size:1.1rem;" title="Verified">✔</span>')
        return format_html('<span style="color:#94a3b8;font-size:1.1rem;" title="Unverified">✘</span>')

    is_verified_icon.short_description = 'Verified'
    is_verified_icon.admin_order_field = 'is_verified'

    def is_staff_icon(self, obj):
        if obj.is_staff:
            return format_html('<span style="color:#f59e0b;font-size:1.1rem;" title="Staff">★</span>')
        return format_html('<span style="color:#e2e8f0;font-size:1.1rem;">★</span>')

    is_staff_icon.short_description = 'Staff'
    is_staff_icon.admin_order_field = 'is_staff'

    def order_count(self, obj):
        """Show number of orders linked to this user"""
        try:
            from payment.models import Order
            count = Order.objects.filter(user=obj).count()
            if count > 0:
                url = (
                    reverse('admin:payment_order_changelist')
                    + f'?user__id__exact={obj.id}'
                )
                return format_html(
                    '<a href="{}" style="color:#2563eb;font-weight:600;">{}</a>',
                    url, count
                )
            return format_html('<span style="color:#94a3b8;">0</span>')
        except Exception:
            return format_html('<span style="color:#94a3b8;">—</span>')

    order_count.short_description = 'Orders'

    def last_login_display(self, obj):
        if obj.last_login:
            delta = timezone.now() - obj.last_login
            if delta.days == 0:
                return format_html(
                    '<span style="color:#10b981;font-size:0.8125rem;">Today</span>'
                )
            elif delta.days <= 7:
                return format_html(
                    '<span style="color:#f59e0b;font-size:0.8125rem;">{} days ago</span>',
                    delta.days
                )
            else:
                return format_html(
                    '<span style="color:#94a3b8;font-size:0.8125rem;">{}</span>',
                    obj.last_login.strftime('%d %b %Y')
                )
        return format_html('<span style="color:#cbd5e1;">Never</span>')

    last_login_display.short_description = 'Last Login'
    last_login_display.admin_order_field = 'last_login'

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            'extended_vendor_profile', 'addresses'
        )


# ============= VENDOR PROFILE ADMIN =============

@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    list_display = (
        'logo_preview', 'store_name', 'user_email',
        'business_phone', 'verification_badge',
        'is_active_icon', 'commission_rate',
        'total_sales', 'rating_display', 'created_at',
    )
    list_filter = (
        'is_active', 'verification_status', 'created_at',
    )
    search_fields = (
        'store_name', 'slug', 'business_email',
        'user__email', 'user__first_name', 'user__last_name',
    )
    prepopulated_fields = {'slug': ('store_name',)}
    readonly_fields = (
        'slug', 'rating', 'total_reviews', 'total_sales',
        'created_at', 'updated_at', 'logo_banner_preview',
    )
    date_hierarchy = 'created_at'
    list_per_page = 25

    fieldsets = (
        ('User Account', {
            'fields': ('user',),
        }),
        ('Store Information', {
            'fields': (
                'store_name', 'slug', 'description',
                'logo_banner_preview', 'logo', 'banner',
            ),
        }),
        ('Business Details', {
            'fields': (
                'business_email', 'business_phone', 'business_address',
                'business_registration_number', 'tax_id',
            ),
        }),
        ('Bank & Payout Information', {
            'fields': (
                'bank_name', 'account_number', 'account_holder_name',
                'bank_code', 'swift_code',
            ),
            'classes': ('collapse',),
        }),
        ('Verification & Status', {
            'fields': (
                'is_active', 'verification_status',
                'verification_date', 'rejection_reason',
            ),
        }),
        ('Commission', {
            'fields': ('commission_rate',),
        }),
        ('Documents', {
            'fields': ('id_document', 'business_license'),
            'classes': ('collapse',),
        }),
        ('Statistics', {
            'fields': ('rating', 'total_reviews', 'total_sales'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    actions = [
        'approve_vendors', 'reject_vendors',
        'activate_vendors', 'deactivate_vendors',
        export_users_csv,
    ]

    # ── Custom display ──

    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" width="44" height="44" '
                'style="object-fit:cover;border-radius:8px;'
                'border:1px solid #e2e8f0;" />',
                obj.logo.url
            )
        return format_html(
            '<div style="width:44px;height:44px;border-radius:8px;'
            'background:#f1f5f9;display:flex;align-items:center;'
            'justify-content:center;color:#94a3b8;font-size:1.25rem;">🏪</div>'
        )

    logo_preview.short_description = ''

    def logo_banner_preview(self, obj):
        html = ''
        if obj.logo:
            html += format_html(
                '<div style="margin-bottom:0.75rem;">'
                '<p style="font-size:0.8125rem;color:#475569;margin-bottom:0.375rem;">Logo</p>'
                '<img src="{}" height="80" '
                'style="object-fit:contain;border-radius:8px;'
                'border:1px solid #e2e8f0;padding:4px;" /></div>',
                obj.logo.url
            )
        if obj.banner:
            html += format_html(
                '<div>'
                '<p style="font-size:0.8125rem;color:#475569;margin-bottom:0.375rem;">Banner</p>'
                '<img src="{}" height="100" style="max-width:400px;object-fit:cover;'
                'border-radius:8px;border:1px solid #e2e8f0;" /></div>',
                obj.banner.url
            )
        return format_html(html) if html else '—'

    logo_banner_preview.short_description = 'Media Preview'

    def user_email(self, obj):
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}" style="color:#2563eb;">{}</a>', url, obj.user.email)

    user_email.short_description = 'Owner Email'
    user_email.admin_order_field = 'user__email'

    def verification_badge(self, obj):
        styles = {
            'pending':      ('background:#fef3c7;color:#b45309;',   'Pending'),
            'under_review': ('background:#dbeafe;color:#1d4ed8;',   'Under Review'),
            'verified':     ('background:#d1fae5;color:#065f46;',   'Verified'),
            'rejected':     ('background:#fee2e2;color:#991b1b;',   'Rejected'),
        }
        style, label = styles.get(
            obj.verification_status,
            ('background:#f1f5f9;color:#475569;', obj.verification_status.title())
        )
        return format_html(
            '<span style="{}padding:3px 10px;border-radius:50px;'
            'font-size:11px;font-weight:700;">{}</span>',
            style, label
        )

    verification_badge.short_description = 'Verification'
    verification_badge.admin_order_field = 'verification_status'

    def is_active_icon(self, obj):
        if obj.is_active:
            return format_html('<span style="color:#10b981;font-weight:700;">Active</span>')
        return format_html('<span style="color:#ef4444;font-weight:700;">Inactive</span>')

    is_active_icon.short_description = 'Status'
    is_active_icon.admin_order_field = 'is_active'

    def rating_display(self, obj):
        if obj.total_reviews > 0:
            stars = '★' * int(obj.rating) + '☆' * (5 - int(obj.rating))
            return format_html(
                '<span style="color:#f59e0b;" title="{} / 5">{}</span>'
                ' <span style="color:#94a3b8;font-size:0.75rem;">({})</span>',
                obj.rating, stars, obj.total_reviews
            )
        return format_html('<span style="color:#cbd5e1;">No reviews</span>')

    rating_display.short_description = 'Rating'

    # ── Actions ──

    def approve_vendors(self, request, queryset):
        updated = queryset.update(
            verification_status='verified',
            is_active=True,
            verification_date=timezone.now()
        )
        self.message_user(request, f'{updated} vendors approved and activated.')

    approve_vendors.short_description = "Approve & activate selected vendors"

    def reject_vendors(self, request, queryset):
        updated = queryset.update(
            verification_status='rejected',
            is_active=False,
        )
        self.message_user(
            request,
            f'{updated} vendors rejected.',
            level=messages.WARNING
        )

    reject_vendors.short_description = "Reject selected vendors"

    def activate_vendors(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} vendors activated.')

    activate_vendors.short_description = "Activate selected vendors"

    def deactivate_vendors(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} vendors deactivated.')

    deactivate_vendors.short_description = "Deactivate selected vendors"


# ============= ADDRESS ADMIN =============

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = (
        'full_name', 'user_email', 'address_type_badge',
        'city', 'country', 'phone',
        'is_default_icon', 'created_at',
    )
    list_filter = (
        'address_type', 'is_default', 'country', 'created_at',
    )
    search_fields = (
        'full_name', 'phone', 'email',
        'city', 'country', 'postal_code',
        'user__email',
    )
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 30

    fieldsets = (
        ('User', {
            'fields': ('user',),
        }),
        ('Address Type', {
            'fields': ('address_type', 'is_default'),
        }),
        ('Contact Information', {
            'fields': ('full_name', 'phone', 'email'),
        }),
        ('Address Details', {
            'fields': (
                'address_line1', 'address_line2',
                'city', 'state', 'postal_code', 'country',
            ),
        }),
        ('Additional', {
            'fields': ('delivery_instructions',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def user_email(self, obj):
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}" style="color:#2563eb;">{}</a>', url, obj.user.email)

    user_email.short_description = 'User'
    user_email.admin_order_field = 'user__email'

    def address_type_badge(self, obj):
        styles = {
            'shipping': ('background:#dbeafe;color:#1d4ed8;', 'Shipping'),
            'billing':  ('background:#fef3c7;color:#b45309;', 'Billing'),
            'both':     ('background:#d1fae5;color:#065f46;', 'Both'),
        }
        style, label = styles.get(
            obj.address_type,
            ('background:#f1f5f9;color:#475569;', obj.address_type.title())
        )
        return format_html(
            '<span style="{}padding:3px 10px;border-radius:50px;'
            'font-size:11px;font-weight:700;">{}</span>',
            style, label
        )

    address_type_badge.short_description = 'Type'
    address_type_badge.admin_order_field = 'address_type'

    def is_default_icon(self, obj):
        if obj.is_default:
            return format_html(
                '<span style="color:#2563eb;font-weight:700;" title="Default">★ Default</span>'
            )
        return format_html('<span style="color:#cbd5e1;">—</span>')

    is_default_icon.short_description = 'Default'
    is_default_icon.admin_order_field = 'is_default'


# ============= SHOP ADMIN =============

@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = (
        'logo_preview', 'name', 'owner_link',
        'subscription_badge', 'is_active_icon',
        'subscription_dates', 'created_at',
    )
    list_filter = (
        'is_active', 'subscription_plan', 'created_at',
    )
    search_fields = ('name', 'slug', 'owner__email')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('slug', 'created_at', 'updated_at')
    list_per_page = 25

    fieldsets = (
        ('Shop Details', {
            'fields': ('name', 'slug', 'owner', 'description', 'logo'),
        }),
        ('Status', {
            'fields': ('is_active',),
        }),
        ('Subscription', {
            'fields': (
                'subscription_plan',
                'subscription_start',
                'subscription_end',
            ),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" width="40" height="40" '
                'style="object-fit:cover;border-radius:8px;'
                'border:1px solid #e2e8f0;" />',
                obj.logo.url
            )
        return format_html(
            '<div style="width:40px;height:40px;border-radius:8px;'
            'background:#f1f5f9;display:flex;align-items:center;'
            'justify-content:center;color:#94a3b8;">🏪</div>'
        )

    logo_preview.short_description = ''

    def owner_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.owner.id])
        return format_html(
            '<a href="{}" style="color:#2563eb;">{}</a>',
            url, obj.owner.get_full_name() or obj.owner.email
        )

    owner_link.short_description = 'Owner'
    owner_link.admin_order_field = 'owner__email'

    def subscription_badge(self, obj):
        styles = {
            'free':       ('background:#f1f5f9;color:#475569;',   'Free'),
            'basic':      ('background:#dbeafe;color:#1d4ed8;',   'Basic'),
            'premium':    ('background:#fef3c7;color:#b45309;',   'Premium'),
            'enterprise': ('background:#ede9fe;color:#6d28d9;',   'Enterprise'),
        }
        style, label = styles.get(
            obj.subscription_plan,
            ('background:#f1f5f9;color:#475569;', obj.subscription_plan.title())
        )
        return format_html(
            '<span style="{}padding:3px 10px;border-radius:50px;'
            'font-size:11px;font-weight:700;">{}</span>',
            style, label
        )

    subscription_badge.short_description = 'Plan'
    subscription_badge.admin_order_field = 'subscription_plan'

    def is_active_icon(self, obj):
        if obj.is_active:
            return format_html('<span style="color:#10b981;font-weight:700;">Active</span>')
        return format_html('<span style="color:#ef4444;font-weight:700;">Inactive</span>')

    is_active_icon.short_description = 'Status'
    is_active_icon.admin_order_field = 'is_active'

    def subscription_dates(self, obj):
        if obj.subscription_start and obj.subscription_end:
            today = timezone.now().date()
            if obj.subscription_end < today:
                color = '#ef4444'
                label = 'Expired'
            elif (obj.subscription_end - today).days <= 14:
                color = '#f59e0b'
                label = f'Expires {obj.subscription_end}'
            else:
                color = '#10b981'
                label = f'Until {obj.subscription_end}'
            return format_html(
                '<span style="color:{};font-size:0.8125rem;">{}</span>',
                color, label
            )
        return format_html('<span style="color:#94a3b8;">—</span>')

    subscription_dates.short_description = 'Subscription'


# ============= ADMIN SITE CUSTOMIZATION =============

admin.site.site_header  = "Homies Platform Admin"
admin.site.site_title   = "Homies Admin Portal"
admin.site.index_title  = "Welcome to Homies Management Dashboard"