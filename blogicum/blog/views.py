from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView
from django.db.models import Count
from .forms import PostForm, CommentForm, ProfileEditForm

from .forms import PostForm, CommentForm
from .models import Category, Post, Comment

User = get_user_model()
POSTS_LIMIT = 10


def get_published_posts():
    return Post.objects.select_related('category', 'location', 'author').filter(
        pub_date__lte=timezone.now(),
        is_published=True,
        category__is_published=True,
    )


def paginate(request, queryset):
    paginator = Paginator(queryset, POSTS_LIMIT)
    return paginator.get_page(request.GET.get('page'))


def index(request):
    post_list = (
        get_published_posts()
        .annotate(comment_count=Count('comments'))
        .order_by('-pub_date')
    )
    page_obj = paginate(request, post_list)
    return render(request, 'blog/index.html', {'page_obj': page_obj})


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        post = get_object_or_404(get_published_posts(), pk=post_id)
    comments = post.comments.select_related('author')
    form = CommentForm()
    return render(request, 'blog/detail.html', {
        'post': post, 'comments': comments, 'form': form,
    })


def category_posts(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug, is_published=True)
    posts = category.posts.select_related('location', 'author').filter(
        pub_date__lte=timezone.now(),
        is_published=True,
    ).annotate(
        comment_count=Count('comments')
    ).order_by('-pub_date')
    return render(request, 'blog/category.html', {
        'category': category,
        'page_obj': paginate(request, posts),
    })


def profile(request, username):
    user = get_object_or_404(User, username=username)
    posts = user.posts.select_related('category', 'location').annotate(
        comment_count=Count('comments')
    ).order_by('-pub_date')
    if request.user != user:
        posts = posts.filter(
            pub_date__lte=timezone.now(),
            is_published=True,
            category__is_published=True,
        ).order_by('-pub_date')
    return render(request, 'blog/profile.html', {
        'profile': user,
        'page_obj': paginate(request, posts),
    })


@login_required
def edit_profile(request):
    form = ProfileEditForm(request.POST or None, instance=request.user)
    if form.is_valid():
        form.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/edit_profile.html', {'form': form})


class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = 'registration/registration_form.html'
    success_url = reverse_lazy('login')


@login_required
def create_post(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)
    form = PostForm(request.POST or None, files=request.FILES or None, instance=post)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, 'blog/create.html', {'form': form})


@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)
    if request.method == 'POST':
        post.delete()
        return redirect('blog:profile', username=request.user.username)
    return render(request, 'blog/detail.html', {'post': post})


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('blog:post_detail', post_id=post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)
    if comment.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)
    form = CommentForm(request.POST or None, instance=comment)
    if form.is_valid():
        form.save()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, 'blog/comment.html', {'form': form, 'comment': comment})


@login_required
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)
    post = comment.post
    if comment.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)
    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', post_id=post_id)
    return render(request, 'blog/comment.html', {'comment': comment})