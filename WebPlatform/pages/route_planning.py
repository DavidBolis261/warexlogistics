import streamlit as st
from datetime import datetime

from config.constants import ZONE_MAPPING


def render(orders_df, drivers_df, runs_df, data_manager):
    st.markdown('<div class="section-header">Route Planning & Runs</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### Create New Run")

        selected_zone = st.selectbox(
            "Select Zone",
            list(ZONE_MAPPING.keys())
        )

        zone_suburbs = ZONE_MAPPING.get(selected_zone, [])

        if not orders_df.empty and 'suburb' in orders_df.columns:
            zone_orders = orders_df[
                (orders_df['suburb'].isin(zone_suburbs)) &
                (orders_df['status'] == 'pending')
            ]
        else:
            zone_orders = orders_df.iloc[0:0]  # empty DataFrame

        st.info(f"{len(zone_orders)} pending orders in {selected_zone}")

        if zone_orders.empty:
            st.warning("No pending orders in this zone. Create orders first or select a different zone.")
        else:
            selected_order_ids = st.multiselect(
                "Select orders for this run",
                zone_orders['order_id'].tolist(),
                default=zone_orders['order_id'].tolist()[:5] if len(zone_orders) > 0 else []
            )

            # Driver selection
            if not drivers_df.empty:
                available_drivers = drivers_df[drivers_df['status'] == 'available']
                if available_drivers.empty:
                    st.warning("No available drivers. Update driver status first.")
                    driver_options = drivers_df['name'].tolist()
                else:
                    driver_options = available_drivers['name'].tolist()
            else:
                driver_options = []
                st.warning("No drivers registered. Add drivers first.")

            if driver_options:
                assigned_driver = st.selectbox("Assign Driver", driver_options)

                # Show selected orders summary
                if selected_order_ids:
                    st.markdown(f"**Run Summary:** {len(selected_order_ids)} stops for {assigned_driver} in {selected_zone}")

                    # Show the selected orders
                    selected_details = zone_orders[zone_orders['order_id'].isin(selected_order_ids)]
                    for _, order in selected_details.iterrows():
                        st.markdown(f"""
                        <div style="padding: 0.5rem; margin: 0.25rem 0; background: rgba(255,255,255,0.05); border-radius: 6px; font-size: 0.85rem;">
                            <strong>{order['order_id']}</strong> &bull; {order['customer']} &bull; {order['address']}, {order['suburb']}
                        </div>
                        """, unsafe_allow_html=True)

                if st.button("Create Run", use_container_width=True, type="primary",
                             disabled=not selected_order_ids):
                    if not selected_order_ids:
                        st.error("Select at least one order for the run.")
                    else:
                        # Get driver_id
                        driver_row = drivers_df[drivers_df['name'] == assigned_driver]
                        driver_id = driver_row.iloc[0]['driver_id'] if not driver_row.empty else assigned_driver

                        result = data_manager.create_run(
                            zone=selected_zone,
                            driver_id=driver_id,
                            driver_name=assigned_driver,
                            order_ids=selected_order_ids,
                        )
                        if result.get('success'):
                            st.success(f"Run {result['run_id']} created with {len(selected_order_ids)} stops assigned to {assigned_driver}")
                            st.rerun()
                        else:
                            st.error("Failed to create run.")

    with col2:
        st.markdown("### Active Runs")

        if runs_df.empty:
            st.info("No runs yet. Create your first run.")
        else:
            active_runs = runs_df[runs_df['status'] == 'active'] if 'status' in runs_df.columns else runs_df

            if active_runs.empty:
                st.info("No active runs.")
            else:
                for _, run in active_runs.iterrows():
                    progress = run.get('progress', 0)
                    progress_color = "#10b981" if progress > 70 else "#fbbf24" if progress > 40 else "#3b82f6"
                    completed = run.get('completed', 0)
                    total_stops = run.get('total_stops', 0)

                    st.markdown(f"""
                    <div class="order-card">
                        <div class="order-id">{run['run_id']}</div>
                        <div class="order-customer">{run.get('driver_name', 'Unassigned')}</div>
                        <div class="order-address">{run.get('zone', '')} &bull; {completed}/{total_stops} stops</div>
                        <div style="margin-top: 0.75rem; background: rgba(255,255,255,0.1); border-radius: 4px; height: 6px; overflow: hidden;">
                            <div style="background: {progress_color}; height: 100%; width: {progress}%;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    # Action buttons per run
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        if st.button("+ Stop", key=f"stop_{run['run_id']}",
                                     use_container_width=True,
                                     disabled=completed >= total_stops):
                            data_manager.update_run_progress(run['run_id'], completed + 1)
                            st.rerun()
                    with col_b:
                        if st.button("Complete", key=f"complete_{run['run_id']}",
                                     use_container_width=True):
                            data_manager.complete_run(run['run_id'])
                            st.success(f"Run {run['run_id']} completed!")
                            st.rerun()
                    with col_c:
                        if st.button("Cancel", key=f"cancel_run_{run['run_id']}",
                                     use_container_width=True):
                            data_manager.cancel_run(run['run_id'])
                            st.info(f"Run {run['run_id']} cancelled. Orders reverted to pending.")
                            st.rerun()

    # Completed / Cancelled Runs
    if not runs_df.empty and 'status' in runs_df.columns:
        past_runs = runs_df[runs_df['status'].isin(['completed', 'cancelled'])]
        if not past_runs.empty:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### Past Runs")

            for _, run in past_runs.head(10).iterrows():
                status_color = "#10b981" if run['status'] == 'completed' else "#ef4444"
                st.markdown(f"""
                <div class="order-card">
                    <div style="display: flex; justify-content: space-between;">
                        <div>
                            <div class="order-id">{run['run_id']}</div>
                            <div class="order-customer">{run.get('driver_name', '')} &bull; {run.get('zone', '')}</div>
                            <div class="order-address">{run.get('completed', 0)}/{run.get('total_stops', 0)} stops</div>
                        </div>
                        <span class="status-badge" style="color: {status_color};">{run['status']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
