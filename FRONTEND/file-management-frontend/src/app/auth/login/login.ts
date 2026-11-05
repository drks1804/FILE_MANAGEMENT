import {
  Component,
  ChangeDetectorRef,
  ElementRef,
  ViewChild,
  OnDestroy
} from '@angular/core';

import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { Router, ActivatedRoute, RouterLink } from '@angular/router';
import { AuthService } from '../auth';
import { environment } from '../../../environments/environment';

interface LoginResponse {
  user_id: number;
  first_name: string;
  last_name: string;
  email: string;
  access_token: string;
}

@Component({
  selector: 'app-login',
  imports: [FormsModule, RouterLink],
  templateUrl: './login.html',
  styleUrl: './login.css'
})
export class Login implements OnDestroy {

  @ViewChild('passwordInput')
  passwordInput!: ElementRef<HTMLInputElement>;

  email = '';
  password = '';

  message = '';
  messageType: 'success' | 'error' = 'error';

  loading = false;
  showPassword = false;

  // Countdown shown after a 429. Purely cosmetic - reflects the last
  // Retry-After value the backend gave for the last attempt made.
  // Nothing is "remembered" per email; the backend is re-asked fresh
  // on every Login click regardless of what this shows.
  remainingSeconds = 0;
  countdownInterval: ReturnType<typeof setInterval> | null = null;

  constructor(
    private http: HttpClient,
    private cdr: ChangeDetectorRef,
    private router: Router,
    private route: ActivatedRoute,
    private authService: AuthService
  ) {}

  private showError(text: string): void {
    this.message = text;
    this.messageType = 'error';
    this.loading = false;
    this.cdr.detectChanges();
  }

  private stopCountdown(): void {

    if (this.countdownInterval) {
      clearInterval(this.countdownInterval);
      this.countdownInterval = null;
    }

    this.remainingSeconds = 0;
  }

  // The previous attempt's message/countdown is stale the moment the
  // user starts editing the form again.
  onFormChange(): void {

    if (this.message || this.remainingSeconds > 0) {
      this.message = '';
      this.stopCountdown();
      this.cdr.detectChanges();
    }
  }

  togglePasswordVisibility(): void {
    this.showPassword = !this.showPassword;
  }

  startCountdown(seconds: number): void {

    this.remainingSeconds = seconds;

    if (this.countdownInterval) {
      clearInterval(this.countdownInterval);
    }

    this.countdownInterval = setInterval(() => {

      if (this.remainingSeconds > 0) {
        this.remainingSeconds--;
      }

      if (this.remainingSeconds === 0) {

        clearInterval(this.countdownInterval!);
        this.countdownInterval = null;
        this.message = '';
      }

      this.cdr.detectChanges();

    }, 1000);
  }

  formatTime(seconds: number): string {

    if (seconds < 60) {
      return `${seconds} ${seconds === 1 ? 'second' : 'seconds'}`;
    }

    const minutes = Math.ceil(seconds / 60);

    return `${minutes} ${minutes === 1 ? 'minute' : 'minutes'}`;
  }

  login(): void {

    if (this.loading) {
      return;
    }

    this.message = '';
    this.stopCountdown();

    if (this.email.trim() === '') {
      this.showError('Please enter a valid email address.');
      return;
    }

    if (this.password === '') {
      this.showError('Password is required.');
      return;
    }

    this.loading = true;
    this.cdr.detectChanges();

    this.http.post<LoginResponse>(
      `${environment.apiUrl}/auth/login`,
      {
        email: this.email,
        password: this.password
      },
      {
        withCredentials: true
      }
    ).subscribe({

      next: response => {

        this.authService.setAccessToken(response.access_token);

        localStorage.setItem('first_name', response.first_name);
        localStorage.setItem('email', response.email.toLowerCase());

        const returnUrl = this.route.snapshot.queryParamMap.get('returnUrl');

        if (returnUrl) {
          this.router.navigateByUrl(returnUrl);
          return;
        }

        this.message = 'Login successful. Opening your files...';
        this.messageType = 'success';

        this.email = '';
        this.password = '';

        this.loading = false;
        this.cdr.detectChanges();

        setTimeout(() => {
          this.router.navigate(['/dashboard/files']);
        }, 600);
      },

      error: error => {

        const detail = error?.error?.detail;

        if (error.status === 0) {
          this.showError('Could not reach the server. Please try again.');
          return;
        }

        if (error.status === 422) {
          this.showError('Please enter a valid email address.');
          return;
        }

        if (error.status === 401) {

          this.password = '';

          this.showError('Incorrect password. Please try again.');

          this.passwordInput?.nativeElement.focus();

          return;
        }

        if (error.status === 404) {

          this.password = '';

          this.showError('Account not found. Please register first.');

          return;
        }

        if (error.status === 429) {

          this.password = '';

          const retryAfter = Number(error.headers.get('Retry-After'));

          if (Number.isFinite(retryAfter) && retryAfter > 0) {

            this.message = 'Too many incorrect attempts. You can try again in:';
            this.messageType = 'error';

            this.loading = false;
            this.cdr.detectChanges();

            this.startCountdown(retryAfter);

          } else {

            this.showError(
              typeof detail === 'string'
                ? detail
                : 'Too many incorrect attempts. Please try again later.'
            );

          }

          return;
        }

        this.showError(
          typeof detail === 'string'
            ? detail
            : 'Something went wrong. Please try again later.'
        );
      }

    });
  }

  ngOnDestroy(): void {
    this.stopCountdown();
  }
}