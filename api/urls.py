from django.urls import path

from . import views

urlpatterns = [
    path("profile/register/", views.profile.RegisterView.as_view()),
    path("profile/login/", views.profile.LoginView.as_view()),
    path("profile/", views.profile.ProfileView.as_view()),
    path("users/", views.profile.UserListView.as_view()),
    path(
        "profile/notifications/", views.profile.NotificationsListView.as_view()
    ),
    path(
        "profile/notifications/read/",
        views.profile.MarkNotificationsReadView.as_view(),
    ),
    path("projects/", views.projects.ProjectListCreateView.as_view()),
    path(
        "projects/<int:pk>/",
        views.projects.ProjectRetrieveUpdateDestroyAPIView.as_view(),
    ),
    path(
        "projects/<int:pk>/posts/",
        views.posts.PostListCreateView.as_view(),
    ),
    path(
        "projects/<int:project>/posts/<int:pk>/",
        views.posts.PostRetrieveUpdateDestroyAPIView.as_view(),
    ),
    path(
        "projects/<int:project>/posts/<int:pk>/preview/",
        views.posts.PostGeneratePreviewView.as_view(),
    ),
    path(
        "projects/<int:project>/posts/<int:post_id>/files/upload/",
        views.posts.UploadFilesView.as_view(),
    ),
    path(
        "projects/<int:project>/posts/<int:post_id>/files/",
        views.posts.PostFileListAPIView.as_view(),
    ),
    path(
        "projects/<int:project>/posts/<int:post_id>/files/<int:pk>/",
        views.posts.PostFileRetrieveDestroyAPIView.as_view(),
    ),
    path(
        "projects/<int:project>/posts/<int:post_id>/stats/<int:days>/",
        views.posts.PostStatListView.as_view(),
    ),
    path(
        "projects/<int:pk>/channels/",
        views.channels.ChannelListCreateView.as_view(),
    ),
    path(
        "projects/<int:project>/channels/<int:pk>/",
        views.channels.ChannelRetrieveUpdateDestroyAPIView.as_view(),
    ),
    path(
        "bindings/add/send_code/", views.binding.BindingSendCodeView.as_view()
    ),
    path(
        "bindings/add/enter_code/",
        views.binding.BindingEnterCodeView.as_view(),
    ),
    path(
        "bindings/add/enter_password/",
        views.binding.BindingEnterPasswordView.as_view(),
    ),
    path("bindings/", views.binding.BindingListAPIView.as_view()),
    path(
        "bindings/<int:pk>/",
        views.binding.BindingRetrieveDestroyAPIView.as_view(),
    ),
    path(
        "bindings/getChannels/",
        views.binding.ChannelFromBindingsListView.as_view(),
    ),
    path(
        "bindings/getChannels/reload/",
        views.binding.BindingsChannelsReloadView.as_view(),
    ),
    path("ai/generate/", views.ai.AIRequestView.as_view(action='generate')),
    path("ai/refactor/", views.ai.AIRequestView.as_view(action='refactor')),
    path(
        "projects/<int:project>/workflow/pushes/",
        views.workflow.WorkflowPushListView.as_view(),
    ),
    path(
        "projects/<int:project>/workflow/stages/",
        views.workflow.WorkflowStageListCreateView.as_view(),
    ),
    path(
        "projects/<int:project>/workflow/stages/<int:pk>/",
        views.workflow.WorkflowStageRetrieveUpdateDestroyAPIView.as_view(),
    ),
    path(
        "calendar/",
        views.posts.GetUpcomingPostsForUser.as_view(),
    ),
]
