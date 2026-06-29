import axios from 'axios';
import { authErrorInterceptor, authRequestInterceptor } from './interceptors';

// NEXT_PUBLIC_API_URL already includes /api/v1
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const coreClient = axios.create({
    baseURL: BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 30000, // Longer timeout for AI responses
});

// Apply interceptors
coreClient.interceptors.request.use(authRequestInterceptor);
coreClient.interceptors.response.use((response) => response, authErrorInterceptor);
