#include <gst/gst.h>
#include <string.h>
#include <stdio.h>
#include <glib.h> 

#define TARGET_LATENCY_MS 100

typedef struct _CustomData {
  gboolean is_live;
  GstElement *playback_pipeline;  // RTSP stream (for video output)
  GstElement *capture_pipeline;   // Webcam stream (for gesture input)
  GMainLoop *loop;
} CustomData;


static void cb_message (GstBus *bus, GstMessage *msg, CustomData *data) {

  switch (GST_MESSAGE_TYPE (msg)) {
    case GST_MESSAGE_ERROR: {
      GError *err;
      gchar *debug;

      gst_message_parse_error (msg, &err, &debug);
      g_print ("\nError: %s\n", err->message);
      g_free (debug); // Must free the debug string
      g_error_free (err);

      // Clean up and quit on any critical error
      gst_element_set_state (data->playback_pipeline, GST_STATE_READY);
      gst_element_set_state (data->capture_pipeline, GST_STATE_READY);
      g_main_loop_quit (data->loop);
      break;
    }
    case GST_MESSAGE_EOS:
      /* End-of-stream. Only critical if the RTSP stream ends. */
      g_print ("\nEnd-of-Stream received.\n");
      gst_element_set_state (data->playback_pipeline, GST_STATE_READY); 
      g_main_loop_quit (data->loop);
      break;
      
    case GST_MESSAGE_BUFFERING: {
      gint percent = 0;

      /* If the stream is live, we do not care about buffering. */
      if (data->is_live) break;

      gst_message_parse_buffering (msg, &percent);
      g_print ("Buffering (%3d%%)\r", percent);
      
      // Control playback pipeline state based on buffering
      if (percent < 100)
        gst_element_set_state (data->playback_pipeline, GST_STATE_PAUSED);
      else
        gst_element_set_state (data->playback_pipeline, GST_STATE_PLAYING);
      break;
    }
    case GST_MESSAGE_CLOCK_LOST:
      /* Get a new clock */
      gst_element_set_state (data->playback_pipeline, GST_STATE_PAUSED);
      gst_element_set_state (data->playback_pipeline, GST_STATE_PLAYING);
      break;

    // -------------------------------------------------------------------
    // CORE LOGIC: INTERCEPT CUSTOM GESTURE MESSAGES
    // -------------------------------------------------------------------
    case GST_MESSAGE_APPLICATION: {
      const GstStructure *s = gst_message_get_structure (msg);
      
      if (gst_structure_has_name (s, "GestureRecognized")) {
          const gchar *gesture_name = NULL;
          gint action_id = -1;
          
          // CORRECTED: Use gst_structure_get() to retrieve multiple typed fields
          gst_structure_get (s, 
                             "gesture_name", G_TYPE_STRING, &gesture_name,
                             "action",       G_TYPE_INT,    &action_id,
                             NULL); // Must terminate with NULL

          g_print("-> GESTURE RECOGNIZED: %s (Action ID: %d)\n", gesture_name, action_id);

          // Execute media control based on the action ID
          if (action_id == 1 /* Play/Pause Toggle */) {
              GstState current_state;
              gst_element_get_state(data->playback_pipeline, &current_state, NULL, 0);

              if (current_state == GST_STATE_PLAYING) {
                  gst_element_set_state(data->playback_pipeline, GST_STATE_PAUSED);
                  g_print("   -> COMMAND EXECUTED: PAUSE\n");
              } else {
                  gst_element_set_state(data->playback_pipeline, GST_STATE_PLAYING);
                  g_print("   -> COMMAND EXECUTED: PLAY\n");
              }
          } 
      }
      break;
    }
  
    default:
      break;
    }
}

int main(int argc, char *argv[]) {
    if(argc < 2)
    {
        printf("Need <ip> argument for the execution: ./program 192.168.1.1\n");
        return -1;
    }
    
  GstElement *playback_pipeline, *capture_pipeline;
  GstBus *playback_bus, *capture_bus;
  GstStateChangeReturn ret;
  GMainLoop *main_loop;
  CustomData data;

  gst_init (&argc, &argv);

  memset (&data, 0, sizeof (data));

    char server[512];
  snprintf(server, sizeof(server), 
        "rtspsrc location=rtsp://%s:8080/h264_pcm.sdp latency=%d ! rtph264depay ! avdec_h264 ! autovideosink",
        argv[1], TARGET_LATENCY_MS);
    
    playback_pipeline = gst_parse_launch (server, NULL);
    if (!playback_pipeline) {
        g_printerr ("Unable to create playback pipeline.\n");
        return -1;
    }
    playback_bus = gst_element_get_bus (playback_pipeline);

    capture_pipeline = gst_parse_launch (
        "autovideosrc ! videoconvert ! video/x-raw,width=640,height=480 ! fakesink", 
        NULL);

    if (!capture_pipeline) {
        g_printerr ("Unable to create capture pipeline. Check your camera.\n");
        gst_object_unref (playback_pipeline);
        return -1;
    }

    capture_bus = gst_element_get_bus (capture_pipeline);

    ret = gst_element_set_state (playback_pipeline, GST_STATE_PLAYING);
    if (ret == GST_STATE_CHANGE_FAILURE) {
      g_printerr ("Unable to set the playback pipeline to the playing state.\n");
      gst_object_unref (playback_pipeline);
      gst_object_unref (capture_pipeline);
      return -1;
    } else if (ret == GST_STATE_CHANGE_NO_PREROLL) {
      data.is_live = TRUE;
    }

    ret = gst_element_set_state (capture_pipeline, GST_STATE_PLAYING);
    if (ret == GST_STATE_CHANGE_FAILURE) {
      g_printerr ("Unable to set the capture pipeline to the playing state.\n");
      gst_object_unref (playback_pipeline);
      gst_object_unref (capture_pipeline);
      return -1;
    }

    main_loop = g_main_loop_new (NULL, FALSE);
    data.loop = main_loop;
    data.playback_pipeline = playback_pipeline; 
    data.capture_pipeline = capture_pipeline;   
    
    gst_bus_add_signal_watch (playback_bus);
    g_signal_connect (playback_bus, "message", G_CALLBACK (cb_message), &data);

    gst_bus_add_signal_watch (capture_bus);
    g_signal_connect (capture_bus, "message", G_CALLBACK (cb_message), &data);

    g_print("GStreamer application running. Waiting for stream/gesture input...\n");
    g_main_loop_run (main_loop);

    g_print("Stopping pipelines and cleaning up...\n");
    g_main_loop_unref (main_loop);
    

    gst_object_unref (playback_bus);
    gst_object_unref (capture_bus); 

    gst_element_set_state (data.playback_pipeline, GST_STATE_NULL);
    gst_object_unref (data.playback_pipeline);
    
    gst_element_set_state (data.capture_pipeline, GST_STATE_NULL);
    gst_object_unref (data.capture_pipeline);
    
    return 0;
}