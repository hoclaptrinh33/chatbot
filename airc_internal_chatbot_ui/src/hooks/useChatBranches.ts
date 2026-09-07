import useChatStore from '@/stores/chatStore';

export function useChatBranches() {
    const { sessions, currentSessionId } = useChatStore();

    const getBranchesAt = (idx: number): string[] => {
        if (!currentSessionId || !sessions) return [];

        let rootId = currentSessionId;
        let current = sessions.find((s) => s.id === currentSessionId);
        while (current && current.parent_id) {
            const parentId = current.parent_id;
            const parent = sessions.find((s) => s.id === parentId);
            if (!parent) break;
            current = parent;
            rootId = current.id;
        }

        const familyIds = [rootId];
        let added = true;
        while (added) {
            added = false;
            for (const s of sessions) {
                if (s.parent_id && familyIds.includes(s.parent_id) && !familyIds.includes(s.id)) {
                    familyIds.push(s.id);
                    added = true;
                }
            }
        }
        const familySessions = sessions.filter((s) => familyIds.includes(s.id));
        const branchSessions = familySessions.filter((s) => s.branch_message_index === idx);
        if (branchSessions.length === 0) return [];
        const parentId = branchSessions[0].parent_id;
        if (!parentId) return [];
        return Array.from(new Set([
            parentId,
            ...familySessions
                .filter((s) => s.parent_id === parentId && s.branch_message_index === idx)
                .map((s) => s.id),
        ]));
    };

    return { getBranchesAt };
}
