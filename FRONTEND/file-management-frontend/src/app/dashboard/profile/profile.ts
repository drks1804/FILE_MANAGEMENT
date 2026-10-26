import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { environment } from '../../../environments/environment';

@Component({
    selector: 'app-profile',
    imports: [FormsModule],
    templateUrl: './profile.html',
    styleUrl: './profile.css',
})
export class Profile implements OnInit {

    firstName = ''
    lastName = ''
    email = ''

    private originalFirstName = ''
    private originalLastName = ''
    private originalEmail = ''

    isEditing = false
    saving = false

    showMessage = false
    message = ''
    messageType: 'success' | 'error' = 'success'

    private emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    constructor(
        private http: HttpClient,
        private cdr: ChangeDetectorRef,
        private router: Router
    ) {}

    ngOnInit() {
        this.getProfile()
    }

    formatName(field: 'firstName' | 'lastName') {

        if (field === 'firstName') {

            this.firstName =
                this.firstName
                    .split(' ')
                    .map(word =>
                        word.charAt(0).toUpperCase() +
                        word.slice(1).toLowerCase()
                    )
                    .join(' ')
        }

        if (field === 'lastName') {

            this.lastName =
                this.lastName
                    .split(' ')
                    .map(word =>
                        word.charAt(0).toUpperCase() +
                        word.slice(1).toLowerCase()
                    )
                    .join(' ')
        }
    }

    getProfile() {

        this.http.get<any>(
            `${environment.apiUrl}/auth/profile`
        ).subscribe({

            next: response => {

                this.firstName = response.first_name
                this.lastName = response.last_name
                this.email = response.email.toLowerCase()

                this.originalFirstName = this.firstName
                this.originalLastName = this.lastName
                this.originalEmail = this.email

                this.cdr.detectChanges()

            },

            error: error => {

                this.showMessagePopup(
                    'Failed to load profile. Please try again.',
                    'error'
                )

            }

        })
    }

    enableEditing() {

        this.isEditing = true
    }

    cancelEditing() {

        this.firstName = this.originalFirstName
        this.lastName = this.originalLastName
        this.email = this.originalEmail

        this.isEditing = false

        this.cdr.detectChanges()
    }

    updateProfile() {

        if (this.saving) {
            return
        }

        if (!this.emailPattern.test(this.email)) {

            this.showMessagePopup(
                'Please enter a valid email address',
                'error'
            )

            return
        }

    const firstName = this.firstName.trim().toLowerCase()
    const lastName = this.lastName.trim().toLowerCase()
    const email = this.email.trim().toLowerCase()

    const originalFirstName = this.originalFirstName.trim().toLowerCase()
    const originalLastName = this.originalLastName.trim().toLowerCase()
    const originalEmail = this.originalEmail.trim().toLowerCase()

    // Check whether anything has changed
    if (
        firstName === originalFirstName &&
        lastName === originalLastName &&
        email === originalEmail
    ) {
        this.isEditing = false

        this.showMessagePopup(
            'Profile updated successfully. No changes detected.',
            'success'
        )

        return
    }

        this.saving = true
        this.cdr.detectChanges()

        const request = {
            first_name: this.firstName.trim(),
            last_name: this.lastName.trim(),
            email: this.email.trim().toLowerCase()
        }

        this.http.patch(
            `${environment.apiUrl}/auth/profile`,
            request
        ).subscribe({

            next: response => {

                this.isEditing = false
                this.saving = false

                this.originalFirstName = this.firstName
                this.originalLastName = this.lastName
                this.originalEmail = this.email

                localStorage.setItem(
                    'first_name',
                    this.firstName
                )

                localStorage.setItem(
                    'email',
                    this.email.toLowerCase()
                )

                this.showMessagePopup(
                    'Profile updated successfully',
                    'success'
                )

                this.cdr.detectChanges()

            },

            error: error => {

                this.saving = false

                if (error.status === 409) {

                    this.showMessagePopup(
                        'Email already registered',
                        'error'
                    )

                } else {

                    this.showMessagePopup(
                        'Failed to update profile. Please try again.',
                        'error'
                    )

                }

                this.cdr.detectChanges()

            }

        })
    }

    goback(){

        const returnUrl = sessionStorage.getItem('prevurl')

        console.log('Saved URL:', returnUrl)

        this.router.navigateByUrl(returnUrl!)

        sessionStorage.removeItem('prevurl')

        console.log('URL after removal:', sessionStorage.getItem('PrevUrl'));

    }

//     goback() {
//     const returnUrl = sessionStorage.getItem('PrevUrl');

//     console.log('Saved URL:', returnUrl);

//     this.router.navigateByUrl(returnUrl!);

//     sessionStorage.removeItem('PrevUrl');

//     console.log('URL after removal:', sessionStorage.getItem('PrevUrl'));
// }

    showMessagePopup(text: string, type: 'success' | 'error' = 'success') {

        this.message = text
        this.messageType = type

        this.showMessage = true

        this.cdr.detectChanges()

        setTimeout(() => {

            this.showMessage = false

            this.cdr.detectChanges()

        }, 3000)
    }
}