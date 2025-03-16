// src/firebase.js
import { initializeApp } from 'firebase/app';

// Your web app's Firebase configuration
const firebaseConfig = {
    apiKey: "AIzaSyA6P2VNQzFrN4cm2dcuAVgcXy18fDkSJ5w",
    authDomain: "margin-calculator-abead.firebaseapp.com",
    projectId: "margin-calculator-abead",
    storageBucket: "margin-calculator-abead.appspot.com",
    messagingSenderId: "1012777467429",
    appId: "1:1012777467429:web:03976ed88c62817f7c89cc"
};

// Initialize Firebase
export const app = initializeApp(firebaseConfig);