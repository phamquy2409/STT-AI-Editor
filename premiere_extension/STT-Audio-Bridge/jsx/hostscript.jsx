var STT128H = STT128H || {};

STT128H.findProjectItemByName = function(parentItem, targetName) {
    if (!parentItem || !parentItem.children) {
        return null;
    }

    for (var i = 0; i < parentItem.children.numItems; i++) {
        var child = parentItem.children[i];

        if (child && child.name === targetName) {
            return child;
        }

        if (child && child.children && child.children.numItems > 0) {
            var nested = STT128H.findProjectItemByName(child, targetName);
            if (nested) {
                return nested;
            }
        }
    }
    return null;
};

STT128H.countVideoClips = function(sequence) {
    var total = 0;

    if (!sequence || !sequence.videoTracks) {
        return 0;
    }

    for (var i = 0; i < sequence.videoTracks.numTracks; i++) {
        var track = sequence.videoTracks[i];
        if (track && track.clips) {
            total += track.clips.numItems;
        }
    }

    return total;
};

STT128H.findTargetAudioTrack = function(sequence) {
    if (!sequence || !sequence.audioTracks) {
        return -1;
    }

    // Prefer A1. Video-only XML already contains an empty A1 track.
    if (sequence.audioTracks.numTracks > 0) {
        return 0;
    }

    return -1;
};

STT128H.chooseAndInsertStereoMusic = function() {
    try {
        if (!app.project) {
            return "ERROR|Chua mo project Premiere.";
        }

        var sequence = app.project.activeSequence;
        if (!sequence) {
            return "ERROR|Hay mo sequence 128H truoc.";
        }

        var videoClipCountBefore = STT128H.countVideoClips(sequence);
        if (videoClipCountBefore < 1) {
            return "ERROR|Sequence hien tai khong co video. Hay import lai stt_128h_VIDEO_ONLY_FINAL.xml.";
        }

        var targetTrackIndex = STT128H.findTargetAudioTrack(sequence);
        if (targetTrackIndex < 0) {
            return "ERROR|Sequence khong co A1. Hay tao 1 Audio Track thuong roi bam lai.";
        }

        var chosen = File.openDialog(
            "Chon file stt_128h_music_STEREO_48K.wav",
            "WAV Stereo:*.wav"
        );

        if (!chosen) {
            return "CANCELLED|Khong chon file.";
        }

        var importBin = app.project.getInsertionBin ?
            app.project.getInsertionBin() :
            app.project.rootItem;

        app.project.importFiles(
            [chosen.fsName],
            1,
            importBin,
            0
        );

        var projectItem = STT128H.findProjectItemByName(
            app.project.rootItem,
            chosen.name
        );

        if (!projectItem) {
            return "ERROR|Da import nhung khong tim thay WAV trong Project.";
        }

        // Critical fix:
        // Do not call QE addTracks/removeVideoTrack.
        // Use the existing A1 so no video track can be deleted.
        sequence.audioTracks[targetTrackIndex].overwriteClip(
            projectItem,
            "0"
        );

        var videoClipCountAfter = STT128H.countVideoClips(sequence);
        if (videoClipCountAfter !== videoClipCountBefore) {
            return "ERROR|So video clip da thay doi bat thuong. Hay Undo ngay.";
        }

        return "OK|Da dat WAV stereo vao A" + (targetTrackIndex + 1) +
               ". Video van giu nguyen.";
    } catch (error) {
        return "ERROR|" + error.toString();
    }
};
