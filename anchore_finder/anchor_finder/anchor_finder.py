import PhotoScan as ps
import cv2
import numpy as np
import os
from PySide2.QtWidgets import *

from common.utils.bridge import camera_coordinates_to_geocentric
from common.utils.markers import get_marker_position_or_location
from common.utils.ui import show_warning_yes_no, ProgressBar


def find_corresponding(res, marker):
    """
    find one nearest marker in found
    """
    markers_before = ps.app.document.chunk.markers[:]
    marker_loc = get_marker_position_or_location(marker)
    ps.Utils.createMarkers(ps.app.document.chunk, res)
    new_markers = [m for m in ps.app.document.chunk.markers if m not in markers_before]
    min_dist = float('inf')
    best = None
    for new_marker in new_markers:
        new_marker_loc = get_marker_position_or_location(new_marker)
        vec = camera_coordinates_to_geocentric(new_marker_loc) - camera_coordinates_to_geocentric(marker_loc)
        dist = np.linalg.norm([vec.x, vec.y])
        if dist < min_dist and np.abs(vec.z) < 1.:
            best = new_marker
            min_dist = dist
    if min_dist < 1.5:
        best.label = marker.label
        best.reference.location = marker.reference.location
        for cam, proj in best.projections.items():
            best.projections[cam].pinned = False
        new_markers.append(marker)
        new_markers.remove(best)

    ps.app.document.chunk.remove(new_markers)


def process_contours(im):
    """
    given found contours check it:
     dbyfourpi - is it circle?
     radius should be the same as in min enclosing circle
     center should be not moved
    """
    im = cv2.cvtColor(im, cv2.COLOR_RGB2GRAY)
    # im = cv2.resize(im, (200, 200))
    ret, thresh = cv2.threshold(im, 230, 255, cv2.THRESH_BINARY)
    im2, contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    res = []
    for cnt in contours:
        M = cv2.moments(cnt)
        if M['m00'] == 0:
            continue
        cx = (M['m10'] / M['m00'])
        cy = (M['m01'] / M['m00'])
        # pi r**2
        a = cv2.contourArea(cnt)
        # 2 pi r
        l = cv2.arcLength(cnt, True)
        (x, y), radius = cv2.minEnclosingCircle(cnt)

        # 4 pi**2 r**2 / pi r**2 == 4 pi
        d = l ** 2 / a
        four_pi = 4 * np.pi
        # 2 pi r**2 / 2 pi r == r
        r = 2 * a / l
        dbyfourpi = d / four_pi
        if dbyfourpi > 3:
            continue
        if np.abs(r - radius) > 3:
            continue
        if np.abs(cx - x) > 3:
            continue
        if np.abs(cy - y) > 3:
            continue
        # cv2.circle(im, (int(x+.5), int(y+.5)), 1, (0, 255, 0), -1)
        # cv2.imshow('w', im)
        # cv2.waitKey()
        # return
        res.append((cx, cy))
    return res


def find_sandclock(im):
    template = cv2.imread(os.path.join(os.path.dirname(__file__), 'pattern.png'))
    w, h = template.shape[:2]
    best_result = -1e30
    template_saved = template.copy()
    for angle in range(-90, 91, 30):
        M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1)
        template = cv2.warpAffine(template_saved, M, (w, h))
        res1 = cv2.matchTemplate(im, template, cv2.TM_CCOEFF)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res1)
        if max_val > best_result:
            best_result = max_val
            top_left = max_loc
    return [(top_left[0] + w // 2, top_left[1] + h // 2)]


def find_projections(projected, cam, object_finder):
    """
    cut small region in projected position and find contours in it
    """
    border = 50
    width = cam.sensor.calibration.width
    height = cam.sensor.calibration.height
    if not projected:
        return []
    if not (0 < projected.x < width and 0 < projected.y < height):
        return []
    proj_x, proj_y = int(projected.x), int(projected.y)
    im = np.fromstring(cam.photo.image().tostring(), dtype=np.uint8)
    w, h = cam.sensor.calibration.width, cam.sensor.calibration.height
    im = im.reshape((h, w, 3))
    diag = np.linalg.norm([w/2, h/2]) * .85
    center_dist = np.linalg.norm([w/2 - proj_x, h/2 - proj_y])
    if center_dist > diag:
        return []
    im = im[proj_y-border:proj_y+border, proj_x-border:proj_x+border]
    if im.shape != (100, 100, 3):
        return []

    cxcy_list = object_finder(im)
    projections_list = []
    for cx, cy in cxcy_list:
        x, y = (proj_x - border + cx + .5), (proj_y - border + cy + .5)
        target = ps.Target()
        target.coord = (x, y)
        projections_list.append((cam, target))
    return projections_list


def find_anchors(anchor_finder):
    """
    find white circled markers in project
    """
    progress = ProgressBar(_("Find anchors"))
    cams = ps.app.document.chunk.cameras
    markers = [m for m in ps.app.document.chunk.markers if m.selected]
    ret = show_warning_yes_no(_("Delete projections?"), _("Do you want to delete existing projections"))
    if ret == QMessageBox.Yes:
        for marker in markers:
            for cam in marker.projections.keys():
                marker.projections[cam] = None
    markers = [m for m in markers if m.reference.location is not None]
    cam_processed = set()
    for idx, marker in enumerate(markers):
        res = []
        marker_loc = get_marker_position_or_location(marker)
        progress.update(idx/len(markers) * 100)
        for cam in cams:
            if not cam.enabled:
                continue
            if cam.label in cam_processed:
                continue
            projected = cam.project(marker_loc)
            r = find_projections(projected, cam, anchor_finder)
            if r:
                res.extend(r)

        find_corresponding(res, marker)

