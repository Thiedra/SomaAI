from django.contrib import admin
from .models import CareerAssessment, CareerRecommendation


class CareerRecommendationInline(admin.TabularInline):
    model = CareerRecommendation
    extra = 0
    readonly_fields = ["id", "career_title", "match_score", "rank"]


@admin.register(CareerAssessment)
class CareerAssessmentAdmin(admin.ModelAdmin):
    list_display = ["student", "created_at", "updated_at"]
    search_fields = ["student__email", "student__full_name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    inlines = [CareerRecommendationInline]


@admin.register(CareerRecommendation)
class CareerRecommendationAdmin(admin.ModelAdmin):
    list_display = ["career_title", "rank", "match_score", "assessment"]
    list_filter = ["rank"]
    search_fields = ["career_title"]
    readonly_fields = ["id"]
