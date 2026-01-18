#include <gst/gst.h>
#include <gst/app/gstappsink.h>
#include <gst/video/video.h>
#include <glib.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#define FRAME_WIDTH 640
#define FRAME_HEIGHT 480
#define FRAME_CHANNELS 3
#define FRAME_SIZE (FRAME_WIDTH * FRAME_HEIGHT * FRAME_CHANNELS)

typedef struct _CustomData {
  GstElement *capture_pipeline;
  GMainLoop *loop;
  GstElement *app_sink;
} CustomData;

static GstFlowReturn pull_sample (GstElement *sink, CustomData *data)
{
  GstSample *sample = gst_app_sink_pull_sample (GST_APP_SINK (sink));
  if (!sample) return GST_FLOW_ERROR;

  GstBuffer *buffer = gst_sample_get_buffer(sample);
  GstCaps *caps = gst_sample_get_caps(sample);
  GstMapInfo map;

  if (!caps) {
    gst_sample_unref(sample);
    return GST_FLOW_ERROR;
  }

  GstVideoInfo vinfo;
  if (!gst_video_info_from_caps(&vinfo, caps)) {
    gst_sample_unref(sample);
    return GST_FLOW_ERROR;
  }

  const guint expected_row_bytes = vinfo.width * FRAME_CHANNELS;
  const guint expected_total_bytes = expected_row_bytes * vinfo.height;

  if (gst_buffer_map(buffer, &map, GST_MAP_READ)) {
    if ((gsize)map.size == expected_total_bytes) {
      write(STDOUT_FILENO, map.data, map.size);
    } else {
      GstVideoFrame vframe;
      if (gst_video_frame_map(&vframe, &vinfo, buffer, GST_MAP_READ)) {
        guint8 *contig = g_malloc(expected_total_bytes);
        guint8 *dst = contig;
        for (guint row = 0; row < vinfo.height; ++row) {
          guint8 *src_row = GST_VIDEO_FRAME_PLANE_DATA(&vframe, 0) + row * GST_VIDEO_FRAME_PLANE_STRIDE(&vframe, 0);
          memcpy(dst, src_row, expected_row_bytes);
          dst += expected_row_bytes;
        }
        write(STDOUT_FILENO, contig, expected_total_bytes);
        g_free(contig);
        gst_video_frame_unmap(&vframe);
      }
    }
    gst_buffer_unmap(buffer, &map);
  }

  gst_sample_unref(sample);
  return GST_FLOW_OK;
}

static void cb_message (GstBus *bus, GstMessage *msg, CustomData *data) {
  switch (GST_MESSAGE_TYPE (msg)) {
    case GST_MESSAGE_ERROR: {
      GError *err;
      gchar *debug;
      gst_message_parse_error (msg, &err, &debug);
      fprintf(stderr, "[GSTREAMER ERROR] %s\n", err->message);
      if (debug) fprintf(stderr, "[GSTREAMER DEBUG] %s\n", debug);
      g_free (debug);
      g_error_free (err);
      gst_element_set_state (data->capture_pipeline, GST_STATE_READY);
      g_main_loop_quit (data->loop);
      break;
    }
    case GST_MESSAGE_EOS:
      fprintf(stderr, "[GSTREAMER INFO] End-of-Stream received.\n");
      g_main_loop_quit (data->loop);
      break;
    case GST_MESSAGE_STATE_CHANGED:
      if (GST_MESSAGE_SRC (msg) == (GstObject*)data->capture_pipeline) {
        GstState old_state, new_state, pending_state;
        gst_message_parse_state_changed (msg, &old_state, &new_state, &pending_state);
        if (new_state == GST_STATE_PLAYING)
          fprintf(stderr, "[GSTREAMER INFO] Pipeline is now playing.\n");
      }
      break;
    default:
      break;
  }
}

int main(int argc, char *argv[]) {
  setvbuf(stdout, NULL, _IONBF, 0);
  if (!gst_app_sink_get_type()) return -1;

  GstElement *capture_pipeline;
  GstBus *capture_bus;
  GstStateChangeReturn ret;
  GMainLoop *main_loop;
  CustomData data;
  gchar *pipeline_desc;

  gst_init (&argc, &argv);
  memset (&data, 0, sizeof (data));


  //Pipeline whihc does not display the vidoe for buidl or cna integrate it as well as the one below
  // pipeline_desc = g_strdup_printf(
  //   "autovideosrc ! tee name=t "
  //   "t. ! queue ! videoconvert ! video/x-raw,width=%d,height=%d,format=RGB ! appsink name=sink ",
  //   FRAME_WIDTH, FRAME_HEIGHT);

  pipeline_desc = g_strdup_printf(
    "autovideosrc ! tee name=t "
    "t. ! queue ! videoconvert ! video/x-raw,width=%d,height=%d,format=RGB ! appsink name=sink "
    "t. ! queue ! videoconvert ! autovideosink sync=false",
    FRAME_WIDTH, FRAME_HEIGHT);

  capture_pipeline = gst_parse_launch(pipeline_desc, NULL);
  g_free(pipeline_desc);
  if (!capture_pipeline) return -1;

  data.app_sink = gst_bin_get_by_name(GST_BIN(capture_pipeline), "sink");
  if (!data.app_sink) {
    gst_object_unref(capture_pipeline);
    return -1;
  }

  g_object_set(data.app_sink, "emit-signals", TRUE, "drop", TRUE, "max-buffers", 2, NULL);

  capture_bus = gst_element_get_bus (capture_pipeline);
  main_loop = g_main_loop_new (NULL, FALSE);
  data.loop = main_loop;
  data.capture_pipeline = capture_pipeline;

  g_signal_connect (data.app_sink, "new-sample", G_CALLBACK (pull_sample), &data);
  gst_bus_add_signal_watch (capture_bus);
  g_signal_connect (capture_bus, "message", G_CALLBACK (cb_message), &data);

  ret = gst_element_set_state (capture_pipeline, GST_STATE_PLAYING);
  if (ret == GST_STATE_CHANGE_FAILURE) {
    gst_object_unref (capture_pipeline);
    return -1;
  }

  fprintf(stderr, "GStreamer Controller running with preview. Framesize: %d bytes.\n", FRAME_SIZE);
  g_main_loop_run (main_loop);

  g_main_loop_unref (main_loop);
  gst_object_unref (capture_bus);
  gst_element_set_state (data.capture_pipeline, GST_STATE_NULL);
  gst_object_unref (data.capture_pipeline);
  return 0;
}
