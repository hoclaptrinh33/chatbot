import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { AxiosError } from 'axios';
import datasetService, { Dataset, DatasetCreatePayload } from '../services/datasetService';

interface DatasetState {
    datasets: Dataset[];
    currentDataset: Dataset | null;
    loading: boolean;
    error: string | null;

    // Actions
    fetchDatasets: () => Promise<void>;
    fetchDataset: (id: string) => Promise<void>;
    createDataset: (payload: DatasetCreatePayload) => Promise<Dataset | null>;
    deleteDataset: (id: string) => Promise<boolean>;
    setCurrentDataset: (dataset: Dataset | null) => void;
}

const useDatasetStore = create<DatasetState>()(
    persist(
        (set) => ({
            datasets: [],
            currentDataset: null,
            loading: false,
            error: null,

            fetchDatasets: async () => {
                set({ loading: true, error: null });
                try {
                    const data = await datasetService.getDatasets();
                    set({ datasets: data, loading: false });
                } catch (error: unknown) {
                    const err = error as AxiosError<{ detail: string }>;
                    console.error('Error fetching datasets:', err);
                    set({
                        loading: false,
                        error: err.response?.data?.detail || 'Khong the tai danh sach datasets'
                    });
                }
            },

            fetchDataset: async (id: string) => {
                set({ loading: true, error: null });
                try {
                    const data = await datasetService.getDataset(id);
                    set({ currentDataset: data, loading: false });
                } catch (error: unknown) {
                    const err = error as AxiosError<{ detail: string }>;
                    console.error('Error fetching dataset:', err);
                    set({
                        loading: false,
                        error: err.response?.data?.detail || 'Khong the tai thong tin dataset'
                    });
                }
            },

            createDataset: async (payload: DatasetCreatePayload) => {
                set({ loading: true, error: null });
                try {
                    const newDataset = await datasetService.createDataset(payload);
                    set((state) => ({
                        datasets: [...state.datasets, newDataset],
                        loading: false
                    }));
                    return newDataset;
                } catch (error: unknown) {
                    const err = error as AxiosError<{ detail: string }>;
                    console.error('Error creating dataset:', err);
                    set({
                        loading: false,
                        error: err.response?.data?.detail || 'Loi khi tao dataset'
                    });
                    return null;
                }
            },

            deleteDataset: async (id: string) => {
                set({ loading: true, error: null });
                try {
                    await datasetService.deleteDataset(id);
                    set((state) => ({
                        datasets: state.datasets.filter(ds => ds.id !== id),
                        loading: false
                    }));
                    return true;
                } catch (error: unknown) {
                    const err = error as AxiosError<{ detail: string }>;
                    console.error('Error deleting dataset:', err);
                    set({
                        loading: false,
                        error: err.response?.data?.detail || 'Loi khi xoa dataset'
                    });
                    return false;
                }
            },

            setCurrentDataset: (dataset) => set({ currentDataset: dataset }),
        }),
        {
            name: 'dataset-storage',
            skipHydration: true, // Prevent SSR mismatch
        }
    )
);

export default useDatasetStore;
